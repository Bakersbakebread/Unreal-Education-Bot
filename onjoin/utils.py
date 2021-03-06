from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
import discord


async def yes_or_no(ctx, message, ) -> bool:
    msg = await ctx.send(message)
    start_adding_reactions(
        msg, ReactionPredicate.YES_OR_NO_EMOJIS,
    )

    pred = ReactionPredicate.yes_or_no(msg, ctx.author, )
    await ctx.bot.wait_for(
        "reaction_add", check=pred,
    )
    await msg.delete()
    return pred.result


async def create_school_options_embed(options: [tuple]) -> discord.Embed:
    """A util to create an embed of available schools to be selected with emoji reactions"""
    embed = discord.Embed(title="Select your school below")
    description = ""
    for index, possible in enumerate(options, 1):
        school_name, probability = possible
        description += f"`{index}` - {school_name}\n"

    embed.description = description
    return embed


async def get_option_reaction(
        ctx, length: int, message: str = None, embed: discord.Embed = None,
):
    """
    Utility method to display get a result action as Type: int for result selected
    on embed or message passed
    """
    if not embed:
        message = f"{ctx.author.mention} {message}"
        msg = await ctx.send(message, delete_after=30, )
    else:
        msg = await ctx.send(ctx.author.mention, embed=embed, delete_after=30, )
    emojis = ReactionPredicate.NUMBER_EMOJIS[1:length]
    start_adding_reactions(
        msg, emojis,
    )

    pred = ReactionPredicate.with_emojis(emojis, msg, ctx.author, )
    react = await ctx.bot.wait_for("reaction_add", check=pred, timeout=30)
    await msg.delete()
    return pred.result


async def joined_school_log_embed(student: discord.Member, school_name: str) -> discord.Embed:
    embed = discord.Embed(
        title="New school signup!",
        color=discord.Color.green()
    )
    embed.add_field(name="Student", value=f"{student} - {student.id}")
    embed.add_field(name="School", value=school_name, inline=False)
    return embed


async def send_mention(destination, author: discord.Member, message: str = None, embed: discord.Embed = None):
    """Util to mention the user when sending a message."""
    if embed is not None:
        await destination.send(f"{author.mention} {message if message else ''}", embed=embed)
    else:
        await destination.send(f"{author.mention} {message}")


# from DEV cog, made by Cog Creators (tekulvw)
def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:-1])

    # remove `foo`
    return content.strip("` \n")
