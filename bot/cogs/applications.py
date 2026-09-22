"""Cog: заявки в клан — Components v2 + модалка."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import disnake
from disnake.ext import commands

import config
from bot.services.app_ticket import create_application_channel, delete_application_channel
from bot.services.apply_panel import APPLY_BUTTON_ID, apply_panel_kwargs
from bot.services.branding import attach_banner_to_embed
from bot.services.channel_style import find_category, find_text_channel
from bot.services.class_roles import assign_class_roles, classes_from_application
from bot.services.onboarding import send_onboarding_dm, send_onboarding_fallback
from bot.services.roles_sync import find_role
from bot.services.wardogs_stats import (
    WardogsStatsError,
    fetch_player_stats,
    normalize_profile_url,
)

REVIEW_APPROVE_ID = "wardogs:app:approve"
REVIEW_REJECT_ID = "wardogs:app:reject"


class ApplicationModal(disnake.ui.Modal):
    def __init__(self, cog: "ApplicationsCog") -> None:
        self.cog = cog
        components = [
            disnake.ui.TextInput(
                label="Ник в WARDOGS",
                custom_id="game_nick",
                placeholder="Ваш игровой ник",
                max_length=32,
            ),
            disnake.ui.TextInput(
                label="Основной класс",
                custom_id="class_name",
                placeholder="Штурмовик / Медик / Поддержка / …",
                max_length=32,
            ),
            disnake.ui.TextInput(
                label="Ссылка wardogs.tools",
                custom_id="profile_url",
                placeholder="https://wardogs.tools/ru/player/… — для статы",
                max_length=220,
            ),
            disnake.ui.TextInput(
                label="Почему хочешь в клан?",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                max_length=400,
            ),
            disnake.ui.TextInput(
                label="Комментарий (опционально)",
                custom_id="experience",
                placeholder="Часы, друзья в клане…",
                max_length=100,
                required=False,
            ),
        ]
        super().__init__(
            title="Заявка в Handler",
            components=components,
            custom_id="wardogs:apply_modal",
        )

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        values = inter.text_values
        await self.cog.submit_application(
            inter,
            game_nick=values.get("game_nick", "").strip(),
            class_name=values.get("class_name", "").strip(),
            profile_url=values.get("profile_url", "").strip(),
            experience=values.get("experience", "").strip(),
            reason=values.get("reason", "").strip(),
        )


def _extract_app_id(inter: disnake.MessageInteraction) -> int | None:
    if inter.message and inter.message.embeds:
        footer = inter.message.embeds[0].footer
        if footer and footer.text and "ID:" in footer.text:
            try:
                return int(footer.text.split("ID:")[1].strip().split()[0])
            except (ValueError, IndexError):
                return None
    return None


class ApplicationsCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    def _normalize_class(self, raw: str) -> str | None:
        return config.resolve_class_key(raw)

    def _is_officer(self, member: disnake.Member) -> bool:
        if member.guild_permissions.administrator:
            return True
        names = {r.name for r in member.roles}
        return config.ROLE_OFFICER in names or config.ROLE_COMMANDER in names

    @commands.slash_command(
        name="заявка",
        description="Панель подачи заявки в клан Handler",
    )
    async def apply_cmd(self, inter: disnake.ApplicationCommandInteraction) -> None:
        await inter.response.send_message(**apply_panel_kwargs())

    @commands.slash_command(
        name="заявка_список",
        description="Список заявок на рассмотрении (офицеры)",
    )
    async def apply_list(self, inter: disnake.ApplicationCommandInteraction) -> None:
        if not isinstance(inter.author, disnake.Member) or not self._is_officer(
            inter.author
        ):
            await inter.response.send_message("Только для офицеров.", ephemeral=True)
            return
        db = self.bot.db  # type: ignore[attr-defined]
        pending = await db.list_pending()
        if not pending:
            await inter.response.send_message("Нет активных заявок.", ephemeral=True)
            return
        lines = [
            f"#{a['id']} — <@{a['user_id']}> · {a['game_nick']} · {a['class']}"
            for a in pending[:25]
        ]
        await inter.response.send_message(
            "**Ожидают решения:**\n" + "\n".join(lines),
            ephemeral=True,
        )

    @commands.Cog.listener("on_button_click")
    async def on_apply_button(self, inter: disnake.MessageInteraction) -> None:
        cid = inter.component.custom_id
        if cid == APPLY_BUTTON_ID:
            await inter.response.send_modal(ApplicationModal(self))
            return
        if cid == REVIEW_APPROVE_ID:
            app_id = _extract_app_id(inter)
            if app_id is None:
                await inter.response.send_message("Не найден ID заявки.", ephemeral=True)
                return
            await self.review(inter, app_id, approve=True)
            return
        if cid == REVIEW_REJECT_ID:
            app_id = _extract_app_id(inter)
            if app_id is None:
                await inter.response.send_message("Не найден ID заявки.", ephemeral=True)
                return
            await self.review(inter, app_id, approve=False)

    async def submit_application(
        self,
        inter: disnake.ModalInteraction | disnake.ApplicationCommandInteraction,
        *,
        game_nick: str,
        class_name: str,
        profile_url: str,
        experience: str,
        reason: str,
    ) -> None:
        if not inter.guild or not isinstance(inter.author, disnake.Member):
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return

        db = self.bot.db  # type: ignore[attr-defined]
        pending = await db.get_pending_by_user(inter.author.id)
        if pending:
            await inter.response.send_message(
                "У тебя уже есть заявка на рассмотрении.", ephemeral=True
            )
            return

        member_role = find_role(inter.guild, config.ROLE_MEMBER)
        if member_role and member_role in inter.author.roles:
            await inter.response.send_message(
                "Ты уже в клане War Dogs.", ephemeral=True
            )
            return

        normalized = self._normalize_class(class_name)
        if not normalized:
            await inter.response.send_message(
                f"Класс должен быть одним из: "
                f"{', '.join(config.class_label_ru(c) for c in config.CLASSES)}",
                ephemeral=True,
            )
            return

        try:
            normalize_profile_url(profile_url)
        except WardogsStatsError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)

        try:
            stats = await fetch_player_stats(profile_url)
        except WardogsStatsError as exc:
            await inter.followup.send(
                f"Не удалось загрузить профиль: {exc}",
                ephemeral=True,
            )
            return
        except Exception:  # noqa: BLE001
            await inter.followup.send(
                "Ошибка при обращении к wardogs.tools. Попробуй позже.",
                ephemeral=True,
            )
            return

        stats_json = json.dumps(stats.to_dict(), ensure_ascii=False)
        app_id = await db.create_application(
            inter.author.id,
            game_nick,
            normalized,
            experience,
            reason,
            profile_url=stats.profile_url,
            stats_json=stats_json,
        )

        recruit = find_role(inter.guild, config.ROLE_RECRUIT)
        if recruit:
            try:
                await inter.author.add_roles(recruit, reason="Заявка в War Dogs")
            except disnake.HTTPException:
                pass

        await db.update_member(
            inter.author.id,
            game_nick=game_nick,
            profile_url=stats.profile_url,
            game_stats_json=stats_json,
            **{"class": normalized},
        )

        embed = disnake.Embed(
            title="Новая заявка в клан",
            color=0xC4A35A,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Discord", value=inter.author.mention, inline=True)
        embed.add_field(name="Ник", value=game_nick, inline=True)
        embed.add_field(name="Класс", value=normalized, inline=True)
        embed.add_field(
            name="Статистика WARDOGS", value=stats.embed_block(), inline=False
        )
        if experience:
            embed.add_field(name="Комментарий", value=experience, inline=False)
        embed.add_field(name="Почему", value=reason, inline=False)
        embed.set_footer(text=f"ID: {app_id}")
        embed.set_thumbnail(url=inter.author.display_avatar.url)
        embed, banner = attach_banner_to_embed(embed, "application_new")

        review_row = disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Одобрить",
                style=disnake.ButtonStyle.success,
                custom_id=REVIEW_APPROVE_ID,
                emoji="✅",
            ),
            disnake.ui.Button(
                label="Отклонить",
                style=disnake.ButtonStyle.danger,
                custom_id=REVIEW_REJECT_ID,
                emoji="✖️",
            ),
        )

        gcfg = await db.get_guild_config(inter.guild.id)
        category = None
        mod_channel = None
        if gcfg:
            cat_id = gcfg.get("categories", {}).get("recruit")
            if cat_id:
                category = inter.guild.get_channel(cat_id)
            mod_channel = inter.guild.get_channel(gcfg["channels"]["mod_apps"])
        if category is None:
            category = find_category(inter.guild, config.CATEGORY_RECRUIT)
        if mod_channel is None:
            mod_channel = find_text_channel(inter.guild, config.CHANNEL_MOD_APPS)

        try:
            ticket = await create_application_channel(
                inter.guild,
                applicant=inter.author,
                app_id=app_id,
                game_nick=game_nick,
                category=category if isinstance(category, disnake.CategoryChannel) else None,
            )
        except disnake.HTTPException:
            await inter.followup.send(
                "Заявка сохранена, но не удалось создать канал. "
                "Проверь права бота (Manage Channels).",
                ephemeral=True,
            )
            return

        ping_roles = []
        for role_name in (config.ROLE_COMMANDER, config.ROLE_OFFICER):
            role = find_role(inter.guild, role_name)
            if role:
                ping_roles.append(role.mention)
        ping_line = " ".join(ping_roles) if ping_roles else ""

        msg = await ticket.send(
            content=(
                f"{inter.author.mention} подал заявку в Handler.\n"
                f"{ping_line}"
            ).strip(),
            embed=embed,
            components=[review_row],
            file=banner,
        )
        await db.set_application_message(app_id, msg.id, channel_id=ticket.id)

        if isinstance(mod_channel, disnake.TextChannel):
            try:
                await mod_channel.send(
                    f"📋 Новая заявка **#{app_id}** от {inter.author.mention} → {ticket.mention}"
                )
            except disnake.HTTPException:
                pass

        await inter.followup.send(
            f"✅ Заявка отправлена → {ticket.mention}\n"
            f"Профиль: **{stats.display_name}** · Wardog **{stats.wardog_level}**\n"
            "Там же можно обсудить заявку с офицерами.",
            ephemeral=True,
        )

    async def review(
        self,
        inter: disnake.MessageInteraction,
        app_id: int,
        *,
        approve: bool,
    ) -> None:
        if not inter.guild or not isinstance(inter.author, disnake.Member):
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return
        if not self._is_officer(inter.author):
            await inter.response.send_message(
                "Только офицеры могут рассматривать заявки.", ephemeral=True
            )
            return

        db = self.bot.db  # type: ignore[attr-defined]
        app = await db.get_application(app_id)
        if not app:
            await inter.response.send_message("Заявка не найдена.", ephemeral=True)
            return
        if app["status"] != "pending":
            await inter.response.send_message(
                f"Заявка уже обработана: `{app['status']}`.", ephemeral=True
            )
            return

        await inter.response.defer()
        status = "approved" if approve else "rejected"
        await db.review_application(app_id, status, inter.author.id)

        applicant_id = int(app["user_id"])
        target = inter.guild.get_member(applicant_id)
        if target is None:
            try:
                target = await inter.guild.fetch_member(applicant_id)
            except disnake.HTTPException:
                target = None

        recruit = find_role(inter.guild, config.ROLE_RECRUIT)
        guest = find_role(inter.guild, config.ROLE_GUEST)
        member_role = find_role(inter.guild, config.ROLE_MEMBER)
        given_classes: list[str] = []

        if approve and target:
            drop = [r for r in (recruit, guest) if r and r in target.roles]
            if drop:
                try:
                    await target.remove_roles(*drop, reason="Принят в War Dogs")
                except disnake.HTTPException:
                    pass
            if member_role:
                try:
                    await target.add_roles(member_role, reason="Принят в War Dogs")
                except disnake.HTTPException:
                    pass
            await db.ensure_member(target.id)
            fields: dict = {
                "game_nick": app["game_nick"],
                "joined_clan_at": datetime.now(timezone.utc).timestamp(),
                "class": app["class"],
            }
            if app.get("profile_url"):
                fields["profile_url"] = app["profile_url"]
            if app.get("stats_json"):
                fields["game_stats_json"] = app["stats_json"]
            await db.update_member(target.id, **fields)
            class_names = classes_from_application(app)
            given_classes = await assign_class_roles(
                target, class_names, reason="Handler: классы по заявке/статистике"
            )
        elif not approve and target:
            if recruit and recruit in target.roles:
                try:
                    await target.remove_roles(recruit, reason="Заявка отклонена")
                except disnake.HTTPException:
                    pass

        # решение — в ЛС подавшему заявку
        dm_ok = False
        if approve:
            user_for_dm: disnake.abc.User | None = target
            if user_for_dm is None:
                user_for_dm = self.bot.get_user(applicant_id)
            if user_for_dm is None:
                try:
                    user_for_dm = await self.bot.fetch_user(applicant_id)
                except disnake.HTTPException:
                    user_for_dm = None
            if user_for_dm is not None:
                dm_ok = await send_onboarding_dm(user_for_dm, db, applicant_id)
            if not dm_ok and target is not None:
                await send_onboarding_fallback(inter.guild, target, db)
                dm_ok = True  # fallback ушёл в канал
        else:
            dm_ok = await self._notify_applicant(
                applicant_id,
                member=target,
                approve=False,
                given_classes=given_classes,
            )

        # уведомление в канал админов
        gcfg = await db.get_guild_config(inter.guild.id)
        mod_channel = None
        if gcfg:
            mod_channel = inter.guild.get_channel(gcfg["channels"].get("mod_apps", 0))
            if mod_channel is None:
                mod_channel = inter.guild.get_channel(gcfg["channels"].get("staff", 0))
        if mod_channel is None:
            mod_channel = find_text_channel(
                inter.guild, config.CHANNEL_MOD_APPS
            ) or find_text_channel(inter.guild, config.CHANNEL_STAFF)

        who = target.mention if target else f"<@{applicant_id}>"
        if approve:
            admin_embed = disnake.Embed(
                title="Заявка принята",
                description=(
                    f"**{who}** принят в **{config.CLAN_NAME}**.\n"
                    f"Ник: **{app['game_nick']}** · класс: **{app['class']}**\n"
                    f"Решение: {inter.author.mention}"
                    + (
                        f"\nКлассы: {', '.join(given_classes)}"
                        if given_classes
                        else ""
                    )
                    + (
                        "\n📬 ЛС кандидату отправлено"
                        if dm_ok
                        else "\n⚠️ ЛС кандидату не доставлено (закрыты сообщения)"
                    )
                ),
                color=0x4A5D23,
                timestamp=datetime.now(timezone.utc),
            )
            admin_key = "application_approved"
        else:
            admin_embed = disnake.Embed(
                title="Заявка отклонена",
                description=(
                    f"**{who}** · **{app['game_nick']}**\n"
                    f"Решение: {inter.author.mention}"
                    + (
                        "\n📬 ЛС кандидату отправлено"
                        if dm_ok
                        else "\n⚠️ ЛС кандидату не доставлено (закрыты сообщения)"
                    )
                ),
                color=0x8B0000,
                timestamp=datetime.now(timezone.utc),
            )
            admin_key = "application_rejected"
        admin_embed.set_footer(text=f"ID заявки: {app_id}")
        admin_embed, admin_banner = attach_banner_to_embed(admin_embed, admin_key)

        if isinstance(mod_channel, disnake.TextChannel):
            try:
                await mod_channel.send(embed=admin_embed, file=admin_banner)
            except disnake.HTTPException:
                pass

        # сначала ответ офицеру — после delete канала followup падает (Unknown Channel)
        title = "Заявка одобрена" if approve else "Заявка отклонена"
        try:
            await inter.followup.send(
                f"{title} (ID {app_id})"
                + (f" · классы: {', '.join(given_classes)}" if given_classes else "")
                + (
                    " · ЛС отправлено кандидату"
                    if dm_ok
                    else " · ЛС кандидату не доставлено (закрыты)"
                )
                + ". Канал заявки будет удалён.",
                ephemeral=True,
            )
        except disnake.HTTPException:
            pass

        ticket_ch = None
        if app.get("channel_id"):
            ticket_ch = inter.guild.get_channel(int(app["channel_id"]))
        if ticket_ch is None and inter.channel:
            ticket_ch = inter.channel
        await delete_application_channel(
            ticket_ch, app_id=app_id, approved=approve
        )

    async def _notify_applicant(
        self,
        applicant_id: int,
        *,
        member: disnake.Member | None,
        approve: bool,
        given_classes: list[str],
    ) -> bool:
        """Шлёт ЛС именно тому, кто подал заявку."""
        user: disnake.abc.User | None = member
        if user is None:
            user = self.bot.get_user(applicant_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(applicant_id)
            except disnake.HTTPException:
                return False

        if approve:
            class_note = (
                f"\nКлассы: **{', '.join(given_classes)}**." if given_classes else ""
            )
            embed = disnake.Embed(
                title="Тебя приняли в Handler",
                description=(
                    f"Добро пожаловать в **{config.CLAN_NAME}**!\n\n"
                    "Твою заявку одобрили — клановые каналы открыты.\n"
                    "Добро пожаловать в стаю."
                    f"{class_note}\n\n"
                    "В канале ролей можно выбрать, за кого играешь.\n"
                    "Профиль: `/профиль` · привязка: `/привязка`"
                ),
                color=0x4A5D23,
            )
            banner_key = "welcome_dm"
        else:
            embed = disnake.Embed(
                title="Заявка отклонена",
                description=(
                    f"Заявка в **{config.CLAN_NAME}** отклонена.\n"
                    "Можешь подать новую позже через `/заявка`."
                ),
                color=0x8B0000,
            )
            banner_key = "rejected_dm"

        embed.set_footer(text="Хендлер · Handler · WARDOGS")
        embed, banner = attach_banner_to_embed(embed, banner_key)
        files: list[disnake.File] = [banner]
        logo_path = config.ASSETS_DIR / "handler-avatar.png"
        if approve and logo_path.exists():
            logo = disnake.File(logo_path, filename="handler-avatar.png")
            embed.set_thumbnail(url="attachment://handler-avatar.png")
            files.append(logo)

        try:
            await user.send(embed=embed, files=files)
            return True
        except disnake.HTTPException:
            return False


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(ApplicationsCog(bot))
