import os
import discord
from discord.ext import commands
from keep_alive import keep_alive
import config_manager
import asyncio
from flask import Flask, request, redirect
import requests

# 啟動 Flask Web 服務保持運行
app = Flask(__name__)


keep_alive()  # 傳入 Flask app

# Discord bot 設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=lambda bot, msg: config_manager.load_config().get("prefix", "!"),
    intents=intents
)

@bot.event
async def on_ready():
    print(f"✅ 機器人已上線：{bot.user}")
    for ext in ["cogs.ping", "cogs.welcome", "cogs.verification", "cogs.copy_message", "cogs.fun_suite"]:
        try:
            await bot.load_extension(ext)
            print(f"✅ 已載入 {ext}")
        except Exception as e:
            print(f"❌ 無法載入 {ext}: {e}")

bot.run(os.getenv("TOKEN"))

