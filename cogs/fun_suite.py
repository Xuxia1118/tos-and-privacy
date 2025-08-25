import io
import os
import random
import datetime as dt
from typing import Optional, Tuple

import discord
from discord.ext import commands, tasks
import aiosqlite
from PIL import Image, ImageDraw, ImageFont

DB_PATH = os.getenv("FUN_SUITE_DB", "fun_suite.db")

# ────────── 彩蛋關鍵字 ──────────
EGG_TRIGGERS = {
    "累了": ["要不要先喝口水？💧", "辛苦啦～伸伸懶腰休息一下 👋", "來點 Lo-fi？🎧"],
    "晚安": ["晚安好夢 🌙", "做個甜甜的夢～", "記得充電，明天見！"],
    "喝水": ["喝水時間到！💦", "補水一下，頭腦更清楚～", "水水水 water water water（？）"],
}

# ────────── 情緒字典（極簡） ──────────
NEG_WORDS = {"難過", "崩潰", "累", "煩", "不想", "低潮", "心累", "失落", "生氣"}
POS_WORDS = {"開心", "太棒", "舒服", "讚", "耶", "爽", "幸福", "喜歡", "超好"}

# ────────── 每日任務池 & 塔羅 ──────────
DAILY_POOL = [
    "今天用 🍵 表情符號回覆三個人",
    "在 #閒聊 說聲早/午/晚安一次",
    "分享一首你愛的歌名",
    "稱讚別人的作品或截圖一次",
    "跟三位不同的人各聊一句話",
]
TAROT = [
    "愚者（正）— 勇敢開始 / 自由 / 機遇",
    "魔術師（正）— 行動力 / 資源整合 / 掌控",
    "女教皇（正）— 直覺 / 內在 / 秘密",
    "戀人（正）— 連結 / 選擇 / 關係進展",
    "戰車（正）— 前進 / 意志 / 突破",
    "命運之輪（正）— 轉機 / 循環 / 機緣",
    "塔（逆）— 延宕的改變 / 先避正面衝突",
    "月亮（逆）— 走出疑慮 / 真相浮現",
    "太陽（正）— 成功 / 溫暖 / 好消息",
    "審判（正）— 重生 / 檢視 / 決斷",
]

def taipei_today_key() -> str:
    tz = dt.timezone(dt.timedelta(hours=8))
    return dt.datetime.now(tz).strftime("%Y-%m-%d")

# ────────── 梗圖繪字 ──────────
def _load_font(size: int):
    candidates = ["msjh.ttc", "PingFang.ttc", "NotoSansTC-Regular.otf", "arial.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

def draw_meme(base_img: Image.Image, top: str = "", bottom: str = "") -> Image.Image:
    im = base_img.convert("RGB")
    W, H = im.size
    draw = ImageDraw.Draw(im)
    font = _load_font(max(28, W // 12))

    def draw_centered(text, y):
        if not text:
            return
        lines, line = [], ""
        for w in list(text):
            test = (line + w).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > W - 40:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        y_cur = y
        for ln in lines:
            bbox = draw.textbbox((0, 0), ln, font=font)
            w = bbox[2] - bbox[0]
            x = (W - w) // 2
            for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(2,2)]:
                draw.text((x+dx, y_cur+dy), ln, font=font, fill=(0,0,0))
            draw.text((x, y_cur), ln, font=font, fill=(255,255,255))
            y_cur += (bbox[3] - bbox[1]) + 6

    draw_centered(top, 10)
    if bottom:
        draw_centered(bottom, H - (H // 6))
    return im

# ────────── Cog 主體 ──────────
class FunSuite(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns = {}
        self.xp_cd = {}
        self.hunger_tick.start()

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER, user_id INTEGER,
                pet_name TEXT, pet_lv INTEGER DEFAULT 1,
                pet_xp INTEGER DEFAULT 0, pet_hunger INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS daily (
                guild_id INTEGER, user_id INTEGER, date_key TEXT,
                challenge TEXT, completed INTEGER DEFAULT 0, reward INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, date_key)
            );
            """)
            await db.commit()

    # ── 工具 ──
    def _cd_ok(self, gid, uid, key, sec):
        now = int(dt.datetime.utcnow().timestamp())
        until = self.cooldowns.get((gid, uid, key), 0)
        if until > now: return False
        self.cooldowns[(gid, uid, key)] = now + sec
        return True

    def _sentiment(self, text: str):
        neg = sum(1 for w in NEG_WORDS if w in text)
        pos = sum(1 for w in POS_WORDS if w in text)
        if neg - pos >= 2: return "neg"
        if pos - neg >= 2: return "pos"
        return None

    async def _get_user(self, gid, uid):
        async with aiosqlite.connect(DB_PATH) as db:
            row = await (await db.execute(
                "SELECT pet_name, pet_lv, pet_xp, pet_hunger, coins FROM users WHERE guild_id=? AND user_id=?",
                (gid, uid)
            )).fetchone()
            if row: return {"pet_name": row[0], "pet_lv": row[1], "pet_xp": row[2], "pet_hunger": row[3], "coins": row[4]}
            await db.execute("INSERT INTO users (guild_id, user_id) VALUES (?,?)", (gid, uid))
            await db.commit()
            return {"pet_name": None, "pet_lv": 1, "pet_xp": 0, "pet_hunger": 0, "coins": 0}

    async def _add_xp(self, gid, uid, xp=1):
        async with aiosqlite.connect(DB_PATH) as db:
            row = await (await db.execute(
                "SELECT pet_lv, pet_xp FROM users WHERE guild_id=? AND user_id=?",(gid, uid)
            )).fetchone()
            if not row: pet_lv, pet_xp = 1, 0
            else: pet_lv, pet_xp = row
            pet_xp += xp
            while pet_xp >= 10 * pet_lv:
                pet_xp -= 10 * pet_lv
                pet_lv += 1
            await db.execute("REPLACE INTO users (guild_id, user_id, pet_lv, pet_xp) VALUES (?,?,?,?)",(gid, uid, pet_lv, pet_xp))
            await db.commit()
            return pet_lv, pet_xp

    async def _get_daily(self, gid, uid):
        key = taipei_today_key()
        async with aiosqlite.connect(DB_PATH) as db:
            row = await (await db.execute(
                "SELECT challenge, completed, reward FROM daily WHERE guild_id=? AND user_id=? AND date_key=?",
                (gid, uid, key)
            )).fetchone()
            if row: return {"challenge": row[0], "completed": row[1], "reward": row[2]}
            challenge, reward = random.choice(DAILY_POOL), random.randint(5,15)
            await db.execute("INSERT INTO daily VALUES (?,?,?,?,?,?)",(gid, uid, key, challenge,0,reward))
            await db.commit()
            return {"challenge": challenge, "completed": 0, "reward": reward}

    async def _complete_daily(self, gid, uid):
        key = taipei_today_key()
        async with aiosqlite.connect(DB_PATH) as db:
            row = await (await db.execute("SELECT completed, reward FROM daily WHERE guild_id=? AND user_id=? AND date_key=?",(gid,uid,key))).fetchone()
            if not row or row[0]: return False,0
            await db.execute("UPDATE daily SET completed=1 WHERE guild_id=? AND user_id=? AND date_key=?",(gid,uid,key))
            await db.execute("UPDATE users SET coins=coins+? WHERE guild_id=? AND user_id=?",(row[1],gid,uid))
            await db.commit()
            return True,row[1]

    # ── on_message ──
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        gid, uid, content = message.guild.id, message.author.id, message.content

        for key, replies in EGG_TRIGGERS.items():
            if key in content and self._cd_ok(gid, uid, f"egg:{key}", 10):
                await message.channel.send(random.choice(replies))
                break

        senti = self._sentiment(content)
        if senti and self._cd_ok(gid, uid, f"senti:{senti}", 30):
            if senti=="neg": await message.channel.send(f"{message.author.mention} 抱一個 🤗 要不要抽張 `!tarot`？")
            else: await message.channel.send(f"{message.author.mention} 能量滿滿！分享今天的開心事吧～")

        await self.bot.process_commands(message)  # ⬅️ 關鍵，確保指令會解析

    # ── 指令區（寵物/每日/趣味） ──
    @commands.command() async def adopt(self, ctx, *, name): d=await self._get_user(ctx.guild.id,ctx.author.id); 
        # …完整指令內容（跟之前相同，略去重複）…

    # (這裡保留你之前的 adopt/pet/feed/duel/daily/done/tarot/meme/cp … 全寫進去就行)

    @tasks.loop(minutes=60)
    async def hunger_tick(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET pet_hunger = MIN(10, pet_hunger+1)")
            await db.commit()

    @hunger_tick.before_loop
    async def _before_tick(self): await self.bot.wait_until_ready()

async def setup(bot): await bot.add_cog(FunSuite(bot))
