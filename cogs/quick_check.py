import os, discord, asyncio, logging
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

intents = discord.Intents.none()  # 連線不需要特權 intents
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ 已登入：{bot.user} ({bot.user.id})")
    # 2 秒後自動關閉，確認能連上即可
    await asyncio.sleep(2)
    await bot.close()

token = os.environ.get("DISCORD_BOT_TOKEN")
if not token:
    raise RuntimeError("DISCORD_BOT_TOKEN 未設定")

bot.run(token)
