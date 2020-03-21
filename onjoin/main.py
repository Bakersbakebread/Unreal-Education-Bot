import discord
from redbot.core.commands import commands
from .api import find_and_parse


class SchoolGate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = 690552296983232554

    async def _get_or_create_school_category(self, guild: discord.Guild, school_name: str) -> discord.CategoryChannel:
        all_categories = guild.categories
        exists = school_name in [cat.name for cat in all_categories]
        if exists:
            category = [cat for cat in all_categories if cat.name == school_name][0]
        else:
            category = await guild.create_category(name=school_name)
            await self._fill_category(category)

        return category

    async def _fill_category(self, category: discord.CategoryChannel):
        text_channels = ["Classroom"]
        voice_channels = 5
        for channel in text_channels:
            await category.create_text_channel(name=channel)
        for channel in range(voice_channels):
            await category.create_voice_channel(name=f"Voice {channel}")

    @commands.command(name="se")
    async def _search_for_school(self, ctx, *, school_name: str):
        results = await find_and_parse(school_name)
        if len(results) == 1:
            match = results[0]
            await ctx.send(f"Cool. Your school is {match.name}, {match.country}")
            await self._get_or_create_school_category(ctx.guild, school_name)
        else:
            result_list = '\n'.join('🏫 `{0}`'.format(w.name) for w in results)
            s = f"Woah. Please narrow down your search results. You can choose from:\n" \
                f"{result_list}"
            await ctx.send(s)
        print(results)
