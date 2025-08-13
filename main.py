import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ROLE_NAME = "乖寶寶"
VERIFY_CHANNEL_ID = 1398732880909434880
TARGET_MESSAGE = "我已完成伺服器名稱更改，且同意遵守一切規則並維護和平友善的環境。"

@bot.event
async def on_ready():
    print(f"✅ 機器人已上線：{bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("機器人在線！✅")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id != VERIFY_CHANNEL_ID:
        await bot.process_commands(message)
        return

    if message.content.strip() == TARGET_MESSAGE:
        member = message.author
        role = discord.utils.get(message.guild.roles, name=ROLE_NAME)

        if not role:
            await message.channel.send("⚠️ 無法找到身分組，請通知管理員。")
            await message.add_reaction("❌")
            return

        if role not in member.roles:
            await member.add_roles(role)

        await message.add_reaction("✅")
    else:
        await message.channel.send(f"{message.author.mention} ⚠️ 請輸入正確的驗證訊息。")
        await message.add_reaction("❌")

    await bot.process_commands(message)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == VERIFY_CHANNEL_ID:
        if message.content.strip() == TARGET_MESSAGE:
            member = message.author
            role = discord.utils.get(message.guild.roles, name=ROLE_NAME)
            if not role:
                await message.channel.send("⚠️ 無法找到身分組，請通知管理員。")
                await message.add_reaction("❌")
                return
            if role not in member.roles:
                await member.add_roles(role)
            await message.add_reaction("✅")
        else:
            await message.channel.send(f"{message.author.mention} ⚠️ 請輸入正確的驗證訊息。")
            await message.add_reaction("❌")
    else:
        # 非驗證頻道：檢查上一則訊息是否相同
        try:
            history = [msg async for msg in message.channel.history(limit=2)]
            if len(history) == 2 and history[1].content == message.content:
                await message.add_reaction("➕")
        except Exception as e:
            print(f"檢查歷史訊息時出錯: {e}")

    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    # 非驗證頻道 且 反應是 ➕
    if reaction.emoji == "➕" and reaction.message.channel.id != VERIFY_CHANNEL_ID:
        message = reaction.message

        # 建立 webhook 模擬玩家發送
        webhook = await message.channel.create_webhook(name=user.display_name)
        await webhook.send(
            content=message.content,
            username=user.display_name,
            avatar_url=user.avatar.url if user.avatar else None
        )
        
        await webhook.delete()

        # 在複製的訊息上也加 ➕
        async for msg in message.channel.history(limit=1):
            await msg.add_reaction("➕")

keep_alive()

bot.run(os.environ["TOKEN"])
