import asyncio
import discord

from redbot.core.commands import commands
from redbot.core import Config
from .utils import yes_or_no, create_school_options_embed, get_option_reaction, joined_school_log_embed
from .api import SearchResult, school_fuzzy_search, parse_result

import logging
log = logging.getLogger("red.unreal.main")


class SchoolGate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = 690552296983232554
        default_guild = {"log_channel": None}
        self.config = Config.get_conf(self, identifier=690552296983232554)
        self.config.register_guild(**default_guild)

    async def _get_or_create_school_category(
        self, guild: discord.Guild, school: SearchResult, role: discord.Role
    ) -> discord.CategoryChannel:
        all_categories = guild.categories
        exists = school.name in [cat.name for cat in all_categories]
        if exists:
            category = [cat for cat in all_categories if cat.name == school.name][0]
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                role: discord.PermissionOverwrite(read_messages=True),
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

    async def _grant_student_access(
        self, guild: discord.Guild, student: discord.Member, school: SearchResult
    ):
        role = await self._get_or_create_school_role(guild, school)
        category = await self._get_or_create_school_category(guild, school, role)

        await student.add_roles(role, reason="Granting access to school")

    async def _send_log_to_channel(self, guild: discord.Guild, student: discord.Member, school: SearchResult):
        """Sends log to channel if set, else fails silently"""
        channel = await self.config.guild(guild).log_channel()
        channel = guild.get_channel(channel)
        if channel is None:
            return
        else:
            embed = await joined_school_log_embed(student, school.name)
            await channel.send(embed=embed)

    @commands.command(name="se")
    async def _search_for_school(self, ctx, *, school_name: str):
        author, guild = ctx.author, ctx.guild
        # if author.roles:
        #     return await ctx.send(f"{author.mention} you're already in a school! Leave that one first.")
        results = await school_fuzzy_search(school_name)
        if len(results) == 0:
            return await ctx.send(f"🤔 Hmm. Couldn't find any school close to that. Try again.")

        options_embed = await create_school_options_embed(results)
        try:
            option_chosen = await get_option_reaction(
            ctx, length=len(results) + 1, embed=options_embed  # we plus 1 here because the enumeration starts at 1
            )
            school, probability = results[option_chosen]
            school_result = await parse_result(school)
            await self._grant_student_access(guild, author, school_result)
            await self._send_log_to_channel(guild, author, school_result)
        except discord.errors.Forbidden as e:
            log.error(f"Tried granting student access, permissions denied to add roles or embed links")
        except discord.errors.NotFound as e:
            log.error(f"Failed to find member to add role {author.id} - {author.name}")
        except asyncio.exceptions.TimeoutError:
            return await ctx.send("⏲ You took too long to respond. Try again.")

    @commands.command(name="setlogger")
    async def _set_logging_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel new joins will be logged"""
        to_set = channel.id if channel is not None else None
        await self.config.guild(ctx.guild).log_channel.set(to_set)
        await ctx.send('👍')