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

@app.route("/callback")
def discord_callback():
    code = request.args.get("code")
    if not code:
        return "Missing code", 400

    # Discord OAuth 交換 Token
    data = {
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv("DISCORD_REDIRECT_URI"),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    if r.status_code != 200:
        return f"Token exchange failed: {r.text}", 400

    tokens = r.json()
    # 這裡你可以存取 tokens["access_token"] 做後續處理

    return "OAuth Success! You can close this page."

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
    for ext in ["cogs.ping", "cogs.welcome", "cogs.verification", "cogs.copy_message"]:
        try:
            await bot.load_extension(ext)
            print(f"✅ 已載入 {ext}")
        except Exception as e:
            print(f"❌ 無法載入 {ext}: {e}")

bot.run(os.getenv("TOKEN"))
