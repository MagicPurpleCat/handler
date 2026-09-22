"""Рейтинг стаи по Wardog level — общая сортировка для витрины и догтага."""

from __future__ import annotations

import json
from typing import Any


def wardog_level(row: dict[str, Any]) -> int:
    raw = row.get("game_stats_json")
    if not raw:
        return -1
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return -1
    lvl = data.get("wardog_level")
    return int(lvl) if isinstance(lvl, int) else -1


def site_rank(row: dict[str, Any]) -> int | None:
    raw = row.get("game_stats_json")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    rank = data.get("rank")
    return int(rank) if isinstance(rank, int) else None


def _sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
    lvl = wardog_level(row)
    rk = site_rank(row)
    tie_rank = rk if rk is not None else 2_000_000_000
    return (-lvl, tie_rank, int(row["discord_id"]))


def ranked_members(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = [r for r in rows if wardog_level(r) >= 0]
    return sorted(eligible, key=_sort_key)


def clan_place(
    rows: list[dict[str, Any]], discord_id: int
) -> tuple[int | None, int]:
    ranked = ranked_members(rows)
    total = len(ranked)
    for place, row in enumerate(ranked, 1):
        if int(row["discord_id"]) == discord_id:
            return place, total
    return None, total
