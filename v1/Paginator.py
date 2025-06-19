"""
Paginator for Discord embeds using discord.py
===
This module provides a simple paginator for navigating through multiple Discord embeds.

"""

import discord as dc
from discord.ui import View, button

class Paginator(View):
    def __init__(self, embeds: list[dc.Embed], *, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current = 0

    async def update_buttons(self, interaction: dc.Interaction):
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @button(label="Previous", style=dc.ButtonStyle.primary)
    async def prev_button(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.current -= 1
        self.current %= len(self.embeds)
        await self.update_buttons(interaction)

    @button(label="Next", style=dc.ButtonStyle.primary)
    async def next_button(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.current += 1
        self.current %= len(self.embeds)
        await self.update_buttons(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.message.edit(view=self)
