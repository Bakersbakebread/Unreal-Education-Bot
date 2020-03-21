import discord
from redbot.core.commands import commands
from .api import find_and_parse, SearchResult


class SchoolGate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = 690552296983232554

    async def _get_or_create_school_category(self, guild: discord.Guild, school: SearchResult, role: discord.Role) -> discord.CategoryChannel:
        all_categories = guild.categories
        exists = school.name in [cat.name for cat in all_categories]
        if exists:
            category = [cat for cat in all_categories if cat.name == school.name][0]
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                role: discord.PermissionOverwrite(read_messages=True)
            }
            category = await guild.create_category(name=school.name, overwrites=overwrites)
            await self._fill_category(category)

        return category

    async def _get_or_create_school_role(self, guild: discord.Guild, school: SearchResult):
        roles = guild.roles
        exists = school.name in [role.name for role in roles]
        if exists:
            role = [role for role in roles if role.name == school.name][0]
        else:
            role = await guild.create_role(reason="New school role", name=school.name, hoist=True)

        return role

    async def _fill_category(self, category: discord.CategoryChannel):
        text_channels = ["Classroom"]
        voice_channels = 5
        for channel in text_channels:
            await category.create_text_channel(name=channel)
        for channel in range(voice_channels):
            await category.create_voice_channel(name=f"Voice {channel}")

    async def _grant_student_access(self, guild: discord.Guild, student: discord.Member, school: SearchResult):
        role = await self._get_or_create_school_role(guild, school)
        category = await self._get_or_create_school_category(guild, school, role)

        await student.add_roles(role, reason="Granting access to school")

    @commands.command(name="se")
    async def _search_for_school(self, ctx, *, school_name: str):
        results = await find_and_parse(school_name)
        if len(results) == 0:
            return await ctx.send(f"🤔 Hmm. Couldn't find any school close to that. Try again.")
        if len(results) == 1:
            match = results[0]
            await ctx.send(f"Cool. Your school is :flag_{match.alpha_code.lower()}:: {match.name}, {match.country}")
            await self._grant_student_access(ctx.guild, ctx.author, match)
        else:
            result_list = '\n'.join('🏫 `{0}`'.format(w.name) for w in results)
            s = f"Woah. Please narrow down your search results. You can choose from:\n" \
                f"{result_list}"
            await ctx.send(s)
        print(results)
