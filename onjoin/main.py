import asyncio
import discord

from redbot.core.commands import commands
from redbot.core import Config, checks
from redbot.core.utils.chat_formatting import box

from .utils import send_mention, create_school_options_embed, get_option_reaction, joined_school_log_embed, yes_or_no
from .api import school_fuzzy_search, CHOICES

import logging
import json
log = logging.getLogger("red.unreal.main")


class NoStudentsException(Exception):
    pass


class SchoolGate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = 690552296983232554
        default_guild = {"log_channel": None, "student_role": None, "custom_choices": [], "school_category": None}
        self.config = Config.get_conf(self, identifier=690552296983232554)
        self.config.register_guild(**default_guild)
        self.bot.remove_command("help")

    @commands.command(name="help")
    async def _replacement_help(self, ctx):
        embed = discord.Embed(title=f"{ctx.guild.name}", color=discord.Color.blue())
        embed.description = f"To use these commands, it is pretty self-explanatory.\n"
        embed.description += \
            (f"`{ctx.prefix}school join school-name`\n"
             "This will fuzzy search a list of known schools for which you can register and gain access to."
             " If your school is not listed, please mention one of the team who will rectify.\n\n")
        embed.description += (
            f"`{ctx.prefix}school leave`\n"
            "This will leave the school you have been registered with.")
        await ctx.send(embed=embed)

    async def _get_or_create_school_channel(
            self, guild: discord.Guild, school: str, role: discord.Role
    ) -> discord.TextChannel:
        all_channels = guild.text_channels
        exists = school in [chan.name for chan in all_channels]
        if exists:
            channel = [cat for cat in all_channels if cat.name == school][0]
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                role: discord.PermissionOverwrite(read_messages=True),
            }
            channel = await guild.create_text_channel(name=school, overwrites=overwrites)

        return channel

    async def _get_or_create_school_role(self, guild: discord.Guild, school: str):
        roles = guild.roles
        exists = school in [role.name for role in roles]
        if exists:
            role = [role for role in roles if role.name == school][0]
        else:
            role = await guild.create_role(reason="New school role", name=school, hoist=True)

        return role

    async def _grant_student_access(
            self, guild: discord.Guild, student: discord.Member, school: str
    ):
        role = await self._get_or_create_school_role(guild, school)
        student_role = await self.config.guild(guild).student_role()
        if student_role is not None:
            student_role = guild.get_role(student_role)
            if student_role is not None:
                await student.add_roles(student_role, reason="Granting access to student role")
        await student.add_roles(role, reason="Granting access to school")
        if len(role.members) < 2:
            raise NoStudentsException()
        await self._get_or_create_school_channel(guild, school, role)

    async def _send_log_to_channel(self, guild: discord.Guild, student: discord.Member, school: str):
        """Sends log to channel if set, else fails silently"""
        channel = await self.config.guild(guild).log_channel()
        channel = guild.get_channel(channel)
        if channel is None:
            return
        else:
            embed = await joined_school_log_embed(student, school)
            await channel.send(embed=embed)

    async def _send_no_students(self, guild, school):
        channel = await self.config.guild(guild).log_channel()
        channel = guild.get_channel(channel)
        if channel is None:
            return
        else:
            embed = discord.Embed(description=f"`{school}` - Not enough students, did not create channels.",
                                  color=discord.Color.red())
            await channel.send(embed=embed)

    @commands.group(name="school", autohelp=False)
    async def school_group(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.bot.get_command("help"))

    @school_group.command(name="join")
    async def _search_for_school(self, ctx, *, school_name: str):
        author, guild = ctx.author, ctx.guild
        school_name = school_name.replace("[", "").replace("]", "")
        if author.roles:
            # role name == category name, so this is their school
            categories = [category.name for category in guild.categories]
            role_names = [role.name for role in author.roles]
            if len([x for x in role_names if x in categories]):
                return await ctx.send(f"{author.mention} you're already in a school! Leave that one first.")
        config_choices = await self.config.guild(guild).custom_choices()
        results = await school_fuzzy_search(school_name, config_choices)
        if len(results) == 0:
            return await send_mention(ctx, author, f"🤔 Hmm. Couldn't find any school close to that. Try again.")

        options_embed = await create_school_options_embed(results)
        try:
            option_chosen = await get_option_reaction(
                ctx, length=len(results) + 1, embed=options_embed  # we plus 1 here because the enumeration starts at 1
            )
            school, probability = results[option_chosen]
            await self._send_log_to_channel(guild, author, school)
            await ctx.send(f"{author.mention}, welcome! You're now in `{school_name}`.")
            await self._grant_student_access(guild, author, school) # throws exception
        except NoStudentsException:
            await self._send_no_students(guild, school_name)
        except discord.errors.Forbidden as e:
            log.error(f"Tried granting student access, permissions denied to add roles or embed links")
        except discord.errors.NotFound as e:
            log.error(f"Failed to find member to add role {author.id} - {author.name}")
        except asyncio.exceptions.TimeoutError:
            return await ctx.send(f"⏲ {author.mention}, you took too long to respond. Try again.")
        finally:
            await ctx.message.delete()

    @school_group.command(name="leave")
    async def _leave_school(self, ctx):
        """Leave your school. """
        author, categories = ctx.author, ctx.guild.categories
        for role in author.roles:
            if role.name.lower() in [n.name.lower() for n in categories]:
                await author.remove_roles(role, reason="Leaving school requested.")
        return await ctx.send(f"{author.mention}, you are no longer part of any school.")

    @commands.command(name="setlogger")
    @checks.mod_or_permissions(manage_messages=True)
    async def _set_logging_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel new joins will be logged"""
        to_set = channel.id if channel is not None else None
        await self.config.guild(ctx.guild).log_channel.set(to_set)
        await ctx.send(f'👍 {to_set}')

    @commands.command(name="setstudent")
    @checks.mod_or_permissions(manage_messages=True)
    async def _set_student_role(self, ctx, role: discord.Role):
        """Set the student role to grant on access to a school"""
        await self.config.guild(ctx.guild).student_role.set(role.id)
        stupid_string = """██████╗  ██████╗ ██╗     ███████╗    ███████╗███████╗████████╗
██╔══██╗██╔═══██╗██║     ██╔════╝    ██╔════╝██╔════╝╚══██╔══╝
██████╔╝██║   ██║██║     █████╗      ███████╗█████╗     ██║   
██╔══██╗██║   ██║██║     ██╔══╝      ╚════██║██╔══╝     ██║   
██║  ██║╚██████╔╝███████╗███████╗    ███████║███████╗   ██║   
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝    ╚══════╝╚══════╝   ╚═╝"""
        await ctx.send(box(f"{stupid_string}\n\nSet the role that students will recieve to: {role} - {role.id}"))

    @commands.command(name="setcategory")
    @checks.mod_or_permissions(manage_messages=True)
    async def _add_category_for_new_classrooms(self, ctx, category: discord.CategoryChannel):
        """Add category where new classrooms shall be created"""
        await self.config.guild(ctx.guild).school_category.set(category.id)
        return await ctx.send(f"👍 Done. New school channels will be created here: `{category}`")

    @checks.mod_or_permissions(manage_messages=True)
    @commands.command(name="addschool")
    async def _add_custom_school(self, ctx, *, school_name):
        """
        Add a custom school to the list of available schools.
        """
        async with self.config.guild(ctx.guild).custom_choices() as custom_choices:
            all_schools = custom_choices + list(CHOICES)
            if school_name in all_schools:
                return await ctx.send(f"{ctx.author.mention}, that school already exists.")

            should_add = await yes_or_no(ctx, f"I'll be adding {school_name} to the list of available schools, are you sure?")
            if not should_add:
                return await ctx.send('Okay.')

            custom_choices.append(school_name)
            return await ctx.send(f"{ctx.author.mention}, `{school_name}` has been added to the list.")

    @commands.command(name="delschool")
    @checks.mod_or_permissions(manage_messages=True)
    async def _delete_custom_school(self, ctx, *, school_name):
        """
        Delete a custom school, not from the list of already available.
        """
        async with self.config.guild(ctx.guild).custom_choices() as custom_choices:
            try:
                custom_choices.remove(school_name)
                return await ctx.send(f":wave: `{school_name}` removed.")
            # EAFP
            except KeyError:
                return await ctx.send(f"😕 `{school_name}` does not exist.")
