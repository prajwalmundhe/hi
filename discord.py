import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

profanity_words = ["badword1", "badword2"]
warned_users = {}  # Stores warnings per user (auto-mute after threshold)

channel_deletion_threshold = 5
ban_threshold = 3
recent_actions = {"channel_deletions": [], "bans": []}

async def cleanup_old_entries(action_type, time_window=10):
    current_time = asyncio.get_event_loop().time()
    recent_actions[action_type] = [t for t in recent_actions[action_type] if current_time - t < time_window]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.command(name='kick')
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'✅ Kicked {member.mention}')
    log_channel = discord.utils.get(ctx.guild.channels, name="logs")
    if log_channel:
        await log_channel.send(f"👢 Kick: {ctx.author.mention} kicked {member.mention}. Reason: {reason}")

@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'✅ Banned {member.mention}')
    log_channel = discord.utils.get(ctx.guild.channels, name="logs")
    if log_channel:
        await log_channel.send(f"🔨 Ban: {ctx.author.mention} banned {member.mention}. Reason: {reason}")

@bot.command(name='mute')
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    mute_role = discord.utils.get(ctx.guild.roles, name='Muted')
    if not mute_role:
        mute_role = await ctx.guild.create_role(name='Muted')
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)
    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f'✅ Muted {member.mention}')
    log_channel = discord.utils.get(ctx.guild.channels, name="logs")
    if log_channel:
        await log_channel.send(f"🔇 Mute: {ctx.author.mention} muted {member.mention}. Reason: {reason}")

@bot.command(name='tempmute')
@commands.has_permissions(manage_roles=True)
async def tempmute(ctx, member: discord.Member, duration: str, *, reason=None):
    mute_role = discord.utils.get(ctx.guild.roles, name='Muted')
    if not mute_role:
        mute_role = await ctx.guild.create_role(name='Muted')
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)

    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f'⏳ Temporarily muted {member.mention} for {duration}. Reason: {reason}')

    # Convert duration to seconds
    time_multiplier = {"s": 1, "m": 60, "h": 3600}
    unit = duration[-1]
    num = int(duration[:-1])

    await asyncio.sleep(num * time_multiplier.get(unit, 60))  # Default to minutes if unit is unknown
    await member.remove_roles(mute_role)
    await ctx.send(f'✅ {member.mention} is now unmuted after {duration}.')

@bot.command(name='warn')
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    warned_users[member.id] = warned_users.get(member.id, 0) + 1
    await ctx.send(f'⚠️ {member.mention}, you have been warned: {reason} ({warned_users[member.id]}/3 warnings)')

    if warned_users[member.id] >= 3:
        mute_role = discord.utils.get(ctx.guild.roles, name='Muted')
        if not mute_role:
            mute_role = await ctx.guild.create_role(name='Muted')
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False)
        await member.add_roles(mute_role)
        await ctx.send(f'🚨 Auto-Muted {member.mention} due to excessive warnings.')

    log_channel = discord.utils.get(ctx.guild.channels, name="logs")
    if log_channel:
        await log_channel.send(f"⚠️ Warn: {ctx.author.mention} warned {member.mention}. Reason: {reason}")

@bot.command(name='nick')
@commands.has_permissions(manage_nicknames=True)
async def change_nickname(ctx, member: discord.Member, *, new_nick: str):
    try:
        old_nick = member.nick if member.nick else member.name
        await member.edit(nick=new_nick)
        await ctx.send(f"✅ Changed nickname for {member.mention} from `{old_nick}` to `{new_nick}`")
        log_channel = discord.utils.get(ctx.guild.channels, name="logs")
        if log_channel:
            await log_channel.send(f"✏️ Nickname Changed: {ctx.author.mention} changed {member.mention}'s nickname from `{old_nick}` to `{new_nick}`.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="📖 Bot Commands", color=discord.Color.blurple())
    embed.add_field(name="🛡️ Moderation", value="`!ban`, `!kick`, `!mute`, `!tempmute`, `!warn`", inline=False)
    embed.add_field(name="🔧 Utility", value="`!nick`", inline=False)
    embed.add_field(name="🚨 Security", value="Auto-Mute on excessive warnings\nAnti-nuke triggers on mass bans/deletes", inline=False)
    embed.set_footer(text="Use !<command> to execute")
    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    for word in profanity_words:
        if word.lower() in message.content.lower():
            await message.delete()
            await message.channel.send(f"{message.author.mention}, message removed due to inappropriate language.")
            log_channel = discord.utils.get(message.guild.channels, name="logs")
            if log_channel:
                await log_channel.send(f"🚫 Message Deleted: {message.author.mention}'s message in {message.channel.mention} contained profanity.")
            break
    await bot.process_commands(message)

bot.run(TOKEN)
