"""Cog: карточка профиля, класс и привязка wardogs.tools."""

from __future__ import annotations

import io
import json

import aiohttp
import disnake
from disnake.ext import commands

import config
from bot.services.branding import attach_banner_to_embed
from bot.services.clan_ladder import clan_place
from bot.services.class_roles import member_play_as_classes
from bot.services.profile_card import render_profile_card
from bot.services.roles_sync import find_role
from bot.services.wardogs_stats import (
    WardogsPlayerStats,
    WardogsStatsError,
    fetch_player_stats,
    normalize_profile_url,
)


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    def _clan_role_label(self, member: disnake.Member) -> str:
        names = {r.name for r in member.roles}
        for name in (
            config.ROLE_COMMANDER,
            config.ROLE_OFFICER,
            config.ROLE_MEMBER,
            config.ROLE_RECRUIT,
            config.ROLE_PAUSE,
            config.ROLE_GUEST,
        ):
            if name in names:
                return name
        return "Гость"

    @commands.slash_command(name="профиль", description="Карточка профиля War Dogs")
    async def profile(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member | None = None,
    ) -> None:
        member = участник or inter.author
        if not isinstance(member, disnake.Member):
            await inter.response.send_message("Участник не найден.", ephemeral=True)
            return

        await inter.response.defer()
        db = self.bot.db  # type: ignore[attr-defined]
        row = await db.ensure_member(member.id)

        game_stats = None
        raw = row.get("game_stats_json")
        if raw:
            try:
                game_stats = json.loads(raw)
            except json.JSONDecodeError:
                game_stats = None

        from datetime import datetime, timedelta, timezone

        since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        activity_sec = await db.activity_seconds_since(member.id, since)
        activity_hours = round(activity_sec / 3600, 1) if activity_sec else 0.0
        reputation = await db.reputation_total(member.id, member.guild.id)

        avatar_bytes: bytes | None = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(member.display_avatar.url)) as resp:
                    if resp.status == 200:
                        avatar_bytes = await resp.read()
        except aiohttp.ClientError:
            avatar_bytes = None

        play_as = member_play_as_classes(member)
        if not play_as and row.get("classes_json"):
            try:
                play_as = [
                    c
                    for c in json.loads(row["classes_json"])
                    if c in config.CLASSES
                ]
            except (json.JSONDecodeError, TypeError):
                play_as = []
        if not play_as and row.get("class"):
            play_as = [row["class"]] if row["class"] in config.CLASSES else []

        ladder_rows = await db.members_with_profile()
        place, total = clan_place(ladder_rows, member.id)

        png = render_profile_card(
            display_name=member.display_name,
            game_nick=row.get("game_nick"),
            class_name=play_as[0] if play_as else row.get("class"),
            play_as_classes=play_as,
            clan_role=self._clan_role_label(member),
            joined_clan_at=row.get("joined_clan_at"),
            avatar_bytes=avatar_bytes,
            game_stats=game_stats,
            activity_hours=activity_hours,
            reputation=reputation,
            clan_place=place,
            clan_total=total,
        )
        file = disnake.File(fp=io.BytesIO(png), filename="profile.png")
        embed = disnake.Embed(
            title=f"Догтаг · {member.display_name}",
            color=0xD4AF37,
        )
        embed.set_image(url="attachment://profile.png")
        logo_path = config.ASSETS_DIR / "handler-avatar.png"
        files = [file]
        if logo_path.exists():
            logo_file = disnake.File(logo_path, filename="handler-avatar.png")
            embed.set_thumbnail(url="attachment://handler-avatar.png")
            files.append(logo_file)
        await inter.followup.send(embed=embed, files=files)

    @commands.slash_command(
        name="привязка",
        description="Связать Discord с профилем wardogs.tools (стата на догтаге)",
    )
    async def link_profile(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @link_profile.sub_command(
        name="установить",
        description="Вставить ссылку профиля — подтянем уровни и классы",
    )
    async def link_set(
        self,
        inter: disnake.ApplicationCommandInteraction,
        ссылка: str = commands.Param(
            name="ссылка",
            description="Адрес с wardogs.tools (можно /ru/player/…)",
        ),
    ) -> None:
        if not isinstance(inter.author, disnake.Member):
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return

        try:
            normalize_profile_url(ссылка)
        except WardogsStatsError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        await self._apply_link(inter, ссылка)

    @link_profile.sub_command(
        name="обновить",
        description="Обновить статистику с уже привязанного профиля",
    )
    async def link_refresh(
        self, inter: disnake.ApplicationCommandInteraction
    ) -> None:
        if not isinstance(inter.author, disnake.Member):
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return

        db = self.bot.db  # type: ignore[attr-defined]
        row = await db.ensure_member(inter.author.id)
        url = row.get("profile_url")
        if not url:
            await inter.response.send_message(
                "Профиль ещё не привязан. Сначала: `/привязка установить`.",
                ephemeral=True,
            )
            return

        await inter.response.defer(ephemeral=True)
        await self._apply_link(inter, url)

    @link_profile.sub_command(
        name="статус",
        description="Показать текущую привязку и краткую стату",
    )
    async def link_status(
        self, inter: disnake.ApplicationCommandInteraction
    ) -> None:
        db = self.bot.db  # type: ignore[attr-defined]
        row = await db.ensure_member(inter.author.id)
        url = row.get("profile_url")
        if not url:
            await inter.response.send_message(
                "Профиль не привязан. Используй `/привязка установить`.",
                ephemeral=True,
            )
            return

        stats_text = f"[Профиль]({url})"
        raw = row.get("game_stats_json")
        if raw:
            try:
                data = json.loads(raw)
                stats = WardogsPlayerStats(
                    profile_url=data.get("profile_url") or url,
                    player_id=data.get("player_id") or "",
                    display_name=data.get("display_name") or "Игрок",
                    rank=data.get("rank"),
                    wardog_level=data.get("wardog_level"),
                    cash=data.get("cash"),
                    xp_total=data.get("xp_total"),
                    season=data.get("season"),
                    roles=data.get("roles") or {},
                    description=data.get("description"),
                    og_image=data.get("og_image"),
                    role_caps=data.get("role_caps") or {},
                    wardog_cap=data.get("wardog_cap"),
                )
                stats_text = stats.embed_block()
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        embed = disnake.Embed(
            title="Привязка профиля",
            description=stats_text,
            color=0x4A5D23,
        )
        embed.add_field(name="Ссылка", value=url, inline=False)
        if row.get("game_nick"):
            embed.add_field(name="Ник в БД", value=row["game_nick"], inline=True)
        await inter.response.send_message(embed=embed, ephemeral=True)

    async def _apply_link(
        self,
        inter: disnake.ApplicationCommandInteraction,
        url: str,
    ) -> None:
        try:
            stats = await fetch_player_stats(url)
        except WardogsStatsError as exc:
            await inter.followup.send(
                f"Не удалось загрузить профиль: {exc}", ephemeral=True
            )
            return
        except Exception:  # noqa: BLE001
            await inter.followup.send(
                "Ошибка при обращении к wardogs.tools. Попробуй позже.",
                ephemeral=True,
            )
            return

        db = self.bot.db  # type: ignore[attr-defined]
        stats_json = json.dumps(stats.to_dict(), ensure_ascii=False)
        fields: dict = {
            "profile_url": stats.profile_url,
            "game_stats_json": stats_json,
            "game_nick": stats.display_name,
        }
        row = await db.ensure_member(inter.author.id)
        if not row.get("class") and stats.roles:
            top = max(stats.roles.items(), key=lambda kv: kv[1])[0]
            for cls in config.CLASSES:
                if cls.upper() == top.upper():
                    fields["class"] = cls
                    break

        await db.update_member(inter.author.id, **fields)

        from bot.cogs.onboarding import mark_onboarding_if_needed

        await mark_onboarding_if_needed(self.bot, inter.author.id, "link")

        embed = disnake.Embed(
            title="Профиль привязан",
            description=(
                "Стата с wardogs.tools на догтаге и в витрине стаи.\n\n"
                + stats.embed_block()
            ),
            color=0x4A5D23,
        )
        embed.set_footer(
            text="Обновить стату: /привязка обновить · карточка: /профиль"
        )
        embed, banner = attach_banner_to_embed(embed, "link")
        await inter.followup.send(embed=embed, file=banner, ephemeral=True)

    @commands.slash_command(name="класс", description="Выбрать основной класс WARDOGS")
    async def set_class(
        self,
        inter: disnake.ApplicationCommandInteraction,
        класс: str = commands.Param(
            name="класс",
            description="Основной класс (полный набор — в #роли)",
            choices=[
                disnake.OptionChoice(name=config.class_label_ru(c), value=c)
                for c in config.CLASSES
            ],
        ),
    ) -> None:
        if not isinstance(inter.author, disnake.Member):
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return
        names = {r.name for r in inter.author.roles}
        member_role = (
            find_role(inter.guild, config.ROLE_MEMBER) if inter.guild else None
        )
        if (
            config.ROLE_MEMBER not in names
            and not inter.author.guild_permissions.administrator
            and not (member_role and member_role in inter.author.roles)
        ):
            await inter.response.send_message(
                "Сначала вступи в клан (роль War Dog).", ephemeral=True
            )
            return
        db = self.bot.db  # type: ignore[attr-defined]
        await db.update_member(
            inter.author.id,
            **{
                "class": класс,
                "classes_json": json.dumps([класс], ensure_ascii=False),
            },
        )
        from bot.services.class_roles import sync_play_as_roles
        from bot.cogs.onboarding import mark_onboarding_if_needed

        await sync_play_as_roles(inter.author, [класс])
        await mark_onboarding_if_needed(self.bot, inter.author.id, "class")
        await inter.response.send_message(
            f"Основной класс: **{config.class_label_ru(класс)}**.\n"
            "Несколько классов можно выбрать в канале ролей.",
            ephemeral=True,
        )


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(ProfileCog(bot))
