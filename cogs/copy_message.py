import asyncio
import logging
from typing import Dict, Optional, Set

import discord
from discord.ext import commands

# 你自己的驗證頻道 ID（在這個頻道內不觸發複製邏輯）
VERIFY_CHANNEL_ID = 1398732880909434880

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CopyMessage(commands.Cog):
    """
    功能：
    1) 偵測同一頻道連續兩則內容相同的訊息，幫第二則加上「➕」。
    2) 當有人對該訊息按「➕」，以該使用者名稱/頭像建立 webhook，複製該訊息。
    3) 會在新的複製訊息上也加「➕」。
    4) 對於同一位使用者，會嘗試移除「上一則他複製出的訊息」的表情符號：
       - 一定會先移除機器人自己加的「➕」(不需要 Manage Messages)；
       - 若具備 Manage Messages 權限，則清空所有反應。
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # 每個 user.id -> 他最後一次複製出來的新訊息 (webhook 的訊息)
        self.last_copied_message: Dict[int, discord.Message] = {}
        # 已經以 webhook 複製過的「原始訊息」ID（避免重複複製）
        self.copied_messages: Set[int] = set()

    # ──────────────────────────────────────────────────────────
    # 事件：新訊息
    # ──────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 忽略機器人與 webhook 自己發的訊息
        if message.author.bot:
            return
        if message.webhook_id:
            return

        # 指定驗證頻道不處理
        if message.channel.id == VERIFY_CHANNEL_ID:
            return

        # 需要讀取歷史權限
        perms = message.channel.permissions_for(message.guild.me)
        if not perms.read_message_history:
            logger.info("[Skip] 缺少 Read Message History 權限")
            return

        try:
            # 取最後兩則訊息（最新的一定是現在的 message）
            history = [msg async for msg in message.channel.history(limit=2)]
            if (
                len(history) == 2
                and history[0].id == message.id
                and history[1].content == message.content
            ):
                # 檢查是否能加反應
                if perms.add_reactions:
                    await message.add_reaction("➕")
                else:
                    logger.info("[Info] 沒有 Add Reactions 權限，無法加反應。")
        except Exception as e:
            logger.exception(f"檢查歷史訊息時出錯: {e}")

    # ──────────────────────────────────────────────────────────
    # 事件：新增反應
    # ──────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        # 忽略機器人自己 & 沒 guild 的私訊
        if user.bot or reaction.message.guild is None:
            return

        message = reaction.message

        # 驗證頻道不處理 & 只處理「➕」
        if reaction.emoji != "➕" or message.channel.id == VERIFY_CHANNEL_ID:
            return

        # 針對原始訊息被按「➕」才進行（避免對 webhook 新訊息再做一次）
        if message.id in self.copied_messages:
            logger.info(f"[Skip] 訊息 {message.id} 已複製過，忽略。")
            return

        guild_me = message.guild.me
        channel_perms = message.channel.permissions_for(guild_me)

        # 檢查必要權限（建立 webhook / 讀歷史 / 加反應）
        if not channel_perms.manage_webhooks:
            logger.info("[Skip] 缺少 Manage Webhooks 權限，無法複製訊息。")
            return
        if not channel_perms.read_message_history:
            logger.info("[Skip] 缺少 Read Message History 權限。")
            return

        try:
            # 使用者頭像
            avatar_url: Optional[str] = str(user.display_avatar.url) if user.display_avatar else None

            # 建立臨時 webhook
            webhook = await message.channel.create_webhook(name=user.display_name)
            try:
                # 用 webhook 轉發內容
                new_msg: discord.Message = await webhook.send(
                    content=message.content,
                    username=user.display_name,
                    avatar_url=avatar_url,
                    wait=True,
                )
            finally:
                # 立刻刪掉 webhook，避免殘留
                await webhook.delete()

            # 給新訊息加上「➕」，方便使用者再次複製/串接流程
            if channel_perms.add_reactions:
                await new_msg.add_reaction("➕")

            # 刪除該使用者上一則複製訊息的表情符號
            await self._cleanup_last_reactions(user_id=user.id, old_msg=self.last_copied_message.get(user.id))

            # 更新狀態
            self.last_copied_message[user.id] = new_msg
            self.copied_messages.add(message.id)

        except discord.Forbidden:
            logger.exception("[Forbidden] 權限不足，無法建立或使用 webhook / 移除反應。")
        except discord.HTTPException as e:
            logger.exception(f"[HTTPException] Discord API 錯誤: {e}")
        except Exception as e:
            logger.exception(f"[Error] 未預期錯誤: {e}")

    # ──────────────────────────────────────────────────────────
    # 內部：清理上一則複製訊息的表情
    # ──────────────────────────────────────────────────────────
    async def _cleanup_last_reactions(self, user_id: int, old_msg: Optional[discord.Message]):
        if not old_msg:
            return

        try:
            # 避免過於緊湊觸發 API 速率限制
            await asyncio.sleep(0.5)

            guild_me = old_msg.guild.me
            perms = old_msg.channel.permissions_for(guild_me)

            # 一定先嘗試移除「機器人自己加的 ➕」（不需要 Manage Messages）
            try:
                await old_msg.remove_reaction("➕", self.bot.user)
            except discord.HTTPException:
                # 可能沒有該反應，略過
                pass

            # 若有 Manage Messages 權限，再清空全部反應（可選）
            if perms.manage_messages:
                try:
                    await old_msg.clear_reactions()
                except discord.HTTPException:
                    logger.info("[Info] clear_reactions() 失敗，可能是目標訊息上沒有反應或權限變動。")
            else:
                logger.info("[Info] 沒有 Manage Messages 權限，僅移除機器人自己的 ➕。")

        except Exception as e:
            logger.exception(f"刪除上一個訊息表情符號時出錯: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(CopyMessage(bot))
