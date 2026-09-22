"""Cog: bootstrap сервера."""

from __future__ import annotations

import disnake
from disnake.ext import commands

import config
from bot.services.bootstrap import bootstrap_guild
from bot.services.branding import attach_banner_to_embed
from bot.services.channel_content import republish_all
from bot.services.channel_style import ensure_styled_names


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    def _is_admin(self, member: disnake.Member) -> bool:
        if member.guild_permissions.administrator:
            return True
        return any(r.name == config.ROLE_COMMANDER for r in member.roles)

    @commands.slash_command(
        name="сервер", description="Управление структурой сервера War Dogs"
    )
    @commands.default_member_permissions(administrator=True)
    async def server(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @server.sub_command(
        name="создать",
        description="Поднять категории, каналы, роли и эмбеды с нуля",
    )
    async def server_create(
        self, inter: disnake.ApplicationCommandInteraction
    ) -> None:
        if not inter.guild or not isinstance(inter.author, disnake.Member):
            await inter.response.send_message(
                "Команда только на сервере.", ephemeral=True
            )
            return
        if not self._is_admin(inter.author):
            await inter.response.send_message(
                "Нужны права администратора или роль Командир.", ephemeral=True
            )
            return

        await inter.response.defer(ephemeral=True)
        try:
            await bootstrap_guild(
                inter.guild,
                self.bot.db,  # type: ignore[attr-defined]
                actor=inter.author,
            )
        except disnake.Forbidden:
            await inter.followup.send(
                "Не хватает прав. Выдай боту **Administrator** и роль выше создаваемых."
            )
            return
        except Exception as exc:  # noqa: BLE001
            await inter.followup.send(f"Ошибка bootstrap: `{exc}`")
            return

        embed = disnake.Embed(
            title="Сервер Handler готов",
            description=(
                f"✅ Сервер **{config.CLAN_NAME}** поднят.\n"
                f"Роль доступа: **{config.ROLE_MEMBER}**.\n"
                f"Заявки: канал `#{config.CHANNEL_APPLY}` или `/заявка`."
            ),
            color=0x4A5D23,
        )
        embed, banner = attach_banner_to_embed(embed, "server_ready")
        await inter.followup.send(embed=embed, file=banner)

    @server.sub_command(
        name="оформление",
        description="Обновить красивые панели в каналах (правила, заявка, роли, тактика, лут)",
    )
    async def server_style(
        self, inter: disnake.ApplicationCommandInteraction
    ) -> None:
        if not inter.guild or not isinstance(inter.author, disnake.Member):
            await inter.response.send_message(
                "Команда только на сервере.", ephemeral=True
            )
            return
        if not self._is_admin(inter.author):
            await inter.response.send_message(
                "Нужны права администратора или роль Командир.", ephemeral=True
            )
            return

        await inter.response.defer(ephemeral=True)
        db = self.bot.db  # type: ignore[attr-defined]
        gcfg = await db.get_guild_config(inter.guild.id)
        me = inter.guild.me or inter.guild.get_member(self.bot.user.id)  # type: ignore[union-attr]
        if me is None:
            await inter.followup.send("Бот не найден на сервере.")
            return

        try:
            renamed = await ensure_styled_names(inter.guild)
            results = await republish_all(inter.guild, me, gcfg)
        except disnake.Forbidden:
            await inter.followup.send(
                "Не хватает прав (Manage Messages / Manage Channels)."
            )
            return
        except Exception as exc:  # noqa: BLE001
            await inter.followup.send(f"Ошибка оформления: `{exc}`")
            return

        lines = [
            f"{'✅' if ok else '⏭'} `{name}`"
            for name, ok in results.items()
        ]
        embed = disnake.Embed(
            title="Оформление каналов",
            description=(
                "Названия и панели Handler обновлены.\n\n"
                f"Переименовано: категории **{renamed['categories']}**, "
                f"текст **{renamed['text']}**, голос **{renamed['voice']}**.\n\n"
                + "\n".join(lines)
            ),
            color=0x4A5D23,
        )
        embed, banner = attach_banner_to_embed(embed, "server_ready")
        await inter.followup.send(embed=embed, file=banner)


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(SetupCog(bot))
