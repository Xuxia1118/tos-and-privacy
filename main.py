import os
import discord
from discord.ext import commands
from keep_alive import keep_alive
from flask import Flask, request
import requests

--- Flask app ---
app = Flask(name)

@app.route("/callback")
def discord_callback():
    code = request.args.get("code")
    if not code:
        return "Missing code", 400

    data = {
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv("DISCORD_REDIRECT_URI"),
    }
    r = requests.post("https://discord.com/api/oauth2/token",
                      data=data,
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        return f"Token exchange failed: {r.text}", 400

    return "OAuth Success! You can close this page."


keep_alive(app)

--- Discord bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    async def setup_hook(self):
        for ext in ["cogs.ping", "cogs.welcome", "cogs.verification", "cogs.copy_message"]:
            try:
                self.load_extension(ext)
                print(f"✅ 已載入 {ext}")
            except Exception as e:
                print(f"❌ 無法載入 {ext}: {e}")

bot = MyBot(
    command_prefix=lambda bot, msg: config_manager.load_config().get("prefix", "!"),
    intents=intents
)

@bot.event
async def on_ready():
    print(f"✅ 機器人已上線：{bot.user}")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
