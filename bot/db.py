"""SQLite-слой бота Хендлер."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    discord_id INTEGER PRIMARY KEY,
    game_nick TEXT,
    class TEXT,
    joined_clan_at REAL,
    profile_url TEXT,
    game_stats_json TEXT,
    onboarding_json TEXT,
    pause_warned_at REAL,
    paused_at REAL,
    classes_json TEXT,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_nick TEXT NOT NULL,
    class TEXT NOT NULL,
    experience TEXT,
    reason TEXT,
    profile_url TEXT,
    stats_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    reviewed_by INTEGER,
    review_note TEXT,
    message_id INTEGER,
    channel_id INTEGER,
    created_at REAL NOT NULL,
    reviewed_at REAL
);

CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER PRIMARY KEY,
    config_json TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_daily (
    discord_id INTEGER NOT NULL,
    day TEXT NOT NULL,
    seconds INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (discord_id, day)
);

CREATE TABLE IF NOT EXISTS staff_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS reputation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


def _utc_day(ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(ts or time.time(), tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config.DB_PATH
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._migrate()
        await self._db.commit()

    async def _migrate(self) -> None:
        statements = (
            "ALTER TABLE members ADD COLUMN profile_url TEXT",
            "ALTER TABLE members ADD COLUMN game_stats_json TEXT",
            "ALTER TABLE members ADD COLUMN onboarding_json TEXT",
            "ALTER TABLE members ADD COLUMN pause_warned_at REAL",
            "ALTER TABLE members ADD COLUMN paused_at REAL",
            "ALTER TABLE members ADD COLUMN classes_json TEXT",
            "ALTER TABLE applications ADD COLUMN profile_url TEXT",
            "ALTER TABLE applications ADD COLUMN stats_json TEXT",
            "ALTER TABLE applications ADD COLUMN channel_id INTEGER",
        )
        for sql in statements:
            try:
                await self.db.execute(sql)
            except aiosqlite.OperationalError:
                pass

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not connected")
        return self._db

    async def ensure_member(self, discord_id: int) -> dict[str, Any]:
        row = await self.get_member(discord_id)
        if row:
            return row
        now = time.time()
        await self.db.execute(
            "INSERT INTO members (discord_id, updated_at) VALUES (?, ?)",
            (discord_id, now),
        )
        await self.db.commit()
        return await self.get_member(discord_id)  # type: ignore[return-value]

    async def get_member(self, discord_id: int) -> dict[str, Any] | None:
        cur = await self.db.execute(
            "SELECT * FROM members WHERE discord_id = ?", (discord_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def update_member(self, discord_id: int, **fields: Any) -> dict[str, Any]:
        await self.ensure_member(discord_id)
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k} = ?" for k in fields)
        await self.db.execute(
            f"UPDATE members SET {cols} WHERE discord_id = ?",
            (*fields.values(), discord_id),
        )
        await self.db.commit()
        return await self.get_member(discord_id)  # type: ignore[return-value]

    async def all_members(self) -> list[dict[str, Any]]:
        cur = await self.db.execute("SELECT * FROM members ORDER BY discord_id")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def members_with_profile(self) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            """
            SELECT * FROM members
            WHERE profile_url IS NOT NULL AND TRIM(profile_url) != ''
            ORDER BY discord_id
            """
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    # --- onboarding ---

    def default_onboarding(self) -> dict[str, bool]:
        return {step: False for step in config.ONBOARDING_STEPS}

    def parse_onboarding(self, row: dict[str, Any] | None) -> dict[str, bool]:
        base = self.default_onboarding()
        if not row:
            return base
        raw = row.get("onboarding_json")
        if not raw:
            return base
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return base
        for step in config.ONBOARDING_STEPS:
            if step in data:
                base[step] = bool(data[step])
        return base

    async def set_onboarding_step(
        self, discord_id: int, step: str, done: bool = True
    ) -> dict[str, bool]:
        row = await self.ensure_member(discord_id)
        steps = self.parse_onboarding(row)
        if step in steps:
            steps[step] = done
        await self.update_member(
            discord_id, onboarding_json=json.dumps(steps, ensure_ascii=False)
        )
        return steps

    async def init_onboarding(self, discord_id: int) -> dict[str, bool]:
        steps = self.default_onboarding()
        await self.update_member(
            discord_id, onboarding_json=json.dumps(steps, ensure_ascii=False)
        )
        return steps

    # --- activity ---

    async def add_activity_seconds(self, discord_id: int, seconds: int) -> None:
        if seconds <= 0:
            return
        day = _utc_day()
        await self.db.execute(
            """
            INSERT INTO activity_daily (discord_id, day, seconds)
            VALUES (?, ?, ?)
            ON CONFLICT(discord_id, day) DO UPDATE SET
                seconds = seconds + excluded.seconds
            """,
            (discord_id, day, seconds),
        )
        await self.db.commit()

    async def activity_seconds_since(
        self, discord_id: int, since_day: str
    ) -> int:
        cur = await self.db.execute(
            """
            SELECT COALESCE(SUM(seconds), 0) AS total
            FROM activity_daily
            WHERE discord_id = ? AND day >= ?
            """,
            (discord_id, since_day),
        )
        row = await cur.fetchone()
        return int(row["total"]) if row else 0

    async def activity_top(self, since_day: str, limit: int = 15) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            """
            SELECT discord_id, SUM(seconds) AS total
            FROM activity_daily
            WHERE day >= ?
            GROUP BY discord_id
            ORDER BY total DESC
            LIMIT ?
            """,
            (since_day, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def last_activity_ts(self, discord_id: int) -> float | None:
        cur = await self.db.execute(
            """
            SELECT day FROM activity_daily
            WHERE discord_id = ? AND seconds > 0
            ORDER BY day DESC LIMIT 1
            """,
            (discord_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        try:
            dt = datetime.strptime(row["day"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            return None

    # --- staff log ---

    async def add_staff_log(
        self, guild_id: int, author_id: int, title: str, body: str
    ) -> int:
        now = time.time()
        cur = await self.db.execute(
            """
            INSERT INTO staff_log (guild_id, author_id, title, body, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, author_id, title, body, now),
        )
        await self.db.commit()
        return int(cur.lastrowid)

    async def list_staff_log(
        self, guild_id: int, limit: int = 10
    ) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            """
            SELECT * FROM staff_log
            WHERE guild_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (guild_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    # --- reputation ---

    async def add_reputation(
        self, guild_id: int, from_id: int, to_id: int, reason: str
    ) -> int:
        now = time.time()
        cur = await self.db.execute(
            """
            INSERT INTO reputation_events
            (guild_id, from_id, to_id, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, from_id, to_id, reason, now),
        )
        await self.db.commit()
        return int(cur.lastrowid)

    async def reputation_total(self, to_id: int, guild_id: int | None = None) -> int:
        if guild_id is not None:
            cur = await self.db.execute(
                """
                SELECT COUNT(*) AS n FROM reputation_events
                WHERE to_id = ? AND guild_id = ?
                """,
                (to_id, guild_id),
            )
        else:
            cur = await self.db.execute(
                "SELECT COUNT(*) AS n FROM reputation_events WHERE to_id = ?",
                (to_id,),
            )
        row = await cur.fetchone()
        return int(row["n"]) if row else 0

    async def reputation_given_today(self, from_id: int, guild_id: int) -> int:
        day_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cur = await self.db.execute(
            """
            SELECT COUNT(*) AS n FROM reputation_events
            WHERE from_id = ? AND guild_id = ? AND created_at >= ?
            """,
            (from_id, guild_id, day_start.timestamp()),
        )
        row = await cur.fetchone()
        return int(row["n"]) if row else 0

    # --- applications ---

    async def create_application(
        self,
        user_id: int,
        game_nick: str,
        class_name: str,
        experience: str,
        reason: str,
        profile_url: str | None = None,
        stats_json: str | None = None,
    ) -> int:
        now = time.time()
        cur = await self.db.execute(
            """
            INSERT INTO applications
            (user_id, game_nick, class, experience, reason, profile_url, stats_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                game_nick,
                class_name,
                experience,
                reason,
                profile_url,
                stats_json,
                now,
            ),
        )
        await self.db.commit()
        return int(cur.lastrowid)

    async def get_application(self, app_id: int) -> dict[str, Any] | None:
        cur = await self.db.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_pending_by_user(self, user_id: int) -> dict[str, Any] | None:
        cur = await self.db.execute(
            "SELECT * FROM applications WHERE user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def list_pending(self) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            "SELECT * FROM applications WHERE status = 'pending' ORDER BY created_at ASC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def set_application_message(
        self,
        app_id: int,
        message_id: int,
        channel_id: int | None = None,
    ) -> None:
        if channel_id is not None:
            await self.db.execute(
                "UPDATE applications SET message_id = ?, channel_id = ? WHERE id = ?",
                (message_id, channel_id, app_id),
            )
        else:
            await self.db.execute(
                "UPDATE applications SET message_id = ? WHERE id = ?",
                (message_id, app_id),
            )
        await self.db.commit()

    async def review_application(
        self,
        app_id: int,
        status: str,
        reviewer_id: int,
        note: str | None = None,
    ) -> dict[str, Any] | None:
        now = time.time()
        await self.db.execute(
            """
            UPDATE applications
            SET status = ?, reviewed_by = ?, review_note = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (status, reviewer_id, note, now, app_id),
        )
        await self.db.commit()
        return await self.get_application(app_id)

    async def save_guild_config(self, guild_id: int, data: dict[str, Any]) -> None:
        now = time.time()
        payload = json.dumps(data, ensure_ascii=False)
        await self.db.execute(
            """
            INSERT INTO guild_config (guild_id, config_json, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                config_json = excluded.config_json,
                updated_at = excluded.updated_at
            """,
            (guild_id, payload, now),
        )
        await self.db.commit()

    async def get_guild_config(self, guild_id: int) -> dict[str, Any] | None:
        cur = await self.db.execute(
            "SELECT config_json FROM guild_config WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return json.loads(row["config_json"])

    async def patch_guild_config(
        self, guild_id: int, **updates: Any
    ) -> dict[str, Any] | None:
        cfg = await self.get_guild_config(guild_id)
        if cfg is None:
            return None
        cfg.update(updates)
        await self.save_guild_config(guild_id, cfg)
        return cfg
