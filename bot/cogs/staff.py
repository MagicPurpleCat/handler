"""Журнал решений штаба."""

from __future__ import annotations

from datetime import datetime, timezone

import disnake
from disnake.ext import commands

import config
from bot.services.branding import attach_banner_to_embed
from bot.services.channel_style import find_text_channel
from bot.services.clan_ranks import is_staff, resolve_channel


class StaffCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    @commands.slash_command(name="штаб", description="Журнал решений штаба")
    async def staff(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @staff.sub_command(name="запись", description="Записать решение в журнал")
    async def staff_add(
        self,
        inter: disnake.ApplicationCommandInteraction,
        тема: str = commands.Param(name="тема", max_length=80),
        решение: str = commands.Param(name="решение", max_length=500),
    ) -> None:
        if not isinstance(inter.author, disnake.Member) or not inter.guild:
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return
        if not is_staff(inter.author):
            await inter.response.send_message(
                "Это только для офицеров и командира.", ephemeral=True
            )
            return

        db = self.bot.db  # type: ignore[attr-defined]
        entry_id = await db.add_staff_log(
            inter.guild.id, inter.author.id, тема.strip(), решение.strip()
        )

        embed = disnake.Embed(
            title=тема.strip(),
            description=решение.strip(),
            color=0x3D5A80,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Журнал · #{entry_id} · {inter.author.display_name}")
        embed, banner = attach_banner_to_embed(embed, "application_approved")

        gcfg = await db.get_guild_config(inter.guild.id)
        channel = resolve_channel(inter.guild, gcfg, "staff")
        if channel is None:
            channel = find_text_channel(inter.guild, config.CHANNEL_STAFF)

        posted = False
        if isinstance(channel, disnake.TextChannel):
            try:
                await channel.send(embed=embed, file=banner)
                posted = True
            except disnake.HTTPException:
                pass

        await inter.response.send_message(
            f"Записал в журнал (#{entry_id})"
            + (f" · пост в {channel.mention}" if posted and channel else ""),
            ephemeral=True,
        )

    @staff.sub_command(name="список", description="Последние записи журнала")
    async def staff_list(
        self,
        inter: disnake.ApplicationCommandInteraction,
        лимит: int = commands.Param(
            name="лимит", default=8, ge=1, le=20
        ),
    ) -> None:
        if not isinstance(inter.author, disnake.Member) or not inter.guild:
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return
        if not is_staff(inter.author):
            await inter.response.send_message(
                "Это только для офицеров и командира.", ephemeral=True
            )
            return

        db = self.bot.db  # type: ignore[attr-defined]
        rows = await db.list_staff_log(inter.guild.id, limit=лимит)
        if not rows:
            await inter.response.send_message(
                "Журнал пуст. Добавь запись: `/штаб запись`.",
                ephemeral=True,
            )
            return

        lines = []
        for row in rows:
            ts = datetime.fromtimestamp(row["created_at"], tz=timezone.utc).strftime(
                "%d.%m %H:%M"
            )
            lines.append(
                f"**#{row['id']}** · {ts} · <@{row['author_id']}>\n"
                f"**{row['title']}** — {row['body'][:120]}"
            )
        embed = disnake.Embed(
            title="Журнал штаба",
            description="\n\n".join(lines),
            color=0x3D5A80,
        )
        await inter.response.send_message(embed=embed, ephemeral=True)


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(StaffCog(bot))
