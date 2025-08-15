import os
import discord
import json
import asyncio
from discord.ext import commands
from keep_alive import keep_alive

# 啟動 Web 服務保持運行
keep_alive()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 讀取 config.json
config_manager.load_config()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=lambda bot, msg: config_manager.config_data["prefix"], intents=intents)


ROLE_NAME = "乖寶寶"
VERIFY_CHANNEL_ID = 1398732880909434880
TARGET_MESSAGE = "我已完成伺服器名稱更改，且同意遵守一切規則並維護和平友善的環境。"

last_copied_message = None
copied_messages = set()

@bot.event
async def on_ready():
    print(f"✅ 機器人已上線：{bot.user}")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(config['welcome_channel_id'])
    if channel:
        await channel.send(config['welcome_message'].replace("{user}", member.mention))

@bot.command()
async def ping(ctx):
    await ctx.send("機器人在線！✅")

@bot.event
async def on_message(message):
    global last_copied_message

    if message.author.bot:
        return

    # 驗證頻道處理
    if message.channel.id == VERIFY_CHANNEL_ID:
        if message.content.strip() == TARGET_MESSAGE:
            role = discord.utils.get(message.guild.roles, name=ROLE_NAME)
            if not role:
                await message.channel.send("⚠️ 無法找到身分組，請通知管理員。")
                await message.add_reaction("❌")
                return
            if role not in message.author.roles:
                await message.author.add_roles(role)
            await message.add_reaction("✅")
        else:
            await message.channel.send(f"{message.author.mention} ⚠️ 請輸入正確的驗證訊息。")
            await message.add_reaction("❌")
    else:
        # 檢查上一則訊息是否相同
        try:
            history = [msg async for msg in message.channel.history(limit=2)]
            if len(history) == 2 and history[1].content == message.content:
                await message.add_reaction("➕")
        except Exception as e:
            print(f"檢查歷史訊息時出錯: {e}")

    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    global last_copied_message

    if user.bot:
        return

    if reaction.emoji == "➕" and reaction.message.channel.id != VERIFY_CHANNEL_ID:
        message = reaction.message

        if message.id in copied_messages:
            print(f"⚠️ 訊息 {message.id} 已經複製過，忽略。")
            return

        webhook = await message.channel.create_webhook(name=user.display_name)
        new_msg = await webhook.send(
            content=message.content,
            username=user.display_name,
            avatar_url=user.avatar.url if user.avatar else None,
            wait=True
        )
        await webhook.delete()

        await new_msg.add_reaction("➕")

        if last_copied_message:
            try:
                await asyncio.sleep(0.5)
                perms = last_copied_message.channel.permissions_for(last_copied_message.guild.me)
                if perms.manage_messages:
                    await last_copied_message.clear_reactions()
            except Exception as e:
                print(f"刪除上一個訊息表情符號時出錯: {e}")

        last_copied_message = new_msg
        copied_messages.add(message.id)

# 啟動機器人 (用環境變數 TOKEN)
bot.run(os.getenv("TOKEN"))
