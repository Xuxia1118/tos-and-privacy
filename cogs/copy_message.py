import asyncio
import discord
from discord.ext import commands

VERIFY_CHANNEL_ID = 1398732880909434880

class CopyMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_copied_message = None
        self.copied_messages = set()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id != VERIFY_CHANNEL_ID:
            try:
                history = [msg async for msg in message.channel.history(limit=2)]
                if len(history) == 2 and history[1].content == message.content:
                    await message.add_reaction("➕")
            except Exception as e:
                print(f"檢查歷史訊息時出錯: {e}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        if reaction.emoji == "➕" and reaction.message.channel.id != VERIFY_CHANNEL_ID:
            message = reaction.message

            if message.id in self.copied_messages:
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

            if self.last_copied_message:
                try:
                    await asyncio.sleep(0.5)
                    perms = self.last_copied_message.channel.permissions_for(self.last_copied_message.guild.me)
                    if perms.manage_messages:
                        await self.last_copied_message.clear_reactions()
                except Exception as e:
                    print(f"刪除上一個訊息表情符號時出錯: {e}")

            self.last_copied_message = new_msg
            self.copied_messages.add(message.id)

async def setup(bot):
    await bot.add_cog(CopyMessage(bot))
