from discord.ext import commands
import config_manager

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cfg = config_manager.load_config()
        channel = self.bot.get_channel(cfg.get('welcome_channel_id'))
        if channel:
            await channel.send(cfg.get('welcome_message', '').replace("{user}", member.mention))

async def setup(bot):
    await bot.add_cog(Welcome(bot))
