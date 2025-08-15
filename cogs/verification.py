import discord
from discord.ext import commands

ROLE_NAME = "乖寶寶"
VERIFY_CHANNEL_ID = 1398732880909434880
TARGET_MESSAGE = "我已完成伺服器名稱更改，且同意遵守一切規則並維護和平友善的環境。"

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

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

async def setup(bot):
    await bot.add_cog(Verification(bot))
