import io
import os
import random
import datetime as dt
from typing import Optional, Tuple

import discord
from discord.ext import commands, tasks
import aiosqlite
from PIL import Image, ImageDraw, ImageFont, Image

DB_PATH = os.getenv("FUN_SUITE_DB", "fun_suite.db")

# ────────── 彩蛋關鍵字（中文用子字串匹配） ──────────
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
        for ch in list(text):
            test = (line + ch).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > W - 40:
                lines.append(line)
                line = ch
            else:
                line = test
        if line:
            lines.append(line)
        y_cur = y
        for ln in lines:
            bbox = draw.textbbox((0, 0), ln, font=font)
            w = bbox[2] - bbox[0]
            x = (W - w) // 2
            # 黑邊白字
            for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(-2,2),(2,-2),(2,2)]:
                draw.text((x+dx, y_cur+dy), ln, font=font, fill=(0,0,0))
            draw.text((x, y_cur), ln, font=font, fill=(255,255,255))
            y_cur += (bbox[3] - bbox[1]) + 6

    draw_centered(top, 10)
    if bottom:
        draw_centered(bottom, H - (H // 6))
    return im

# ────────── Cog 主體 ──────────
class FunSuite(commands.Cog):
    """彩蛋 / 情緒互動 / 寵物 / 每日任務 / 趣味工具"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns: dict[tuple[int,int,str], int] = {}
        self.xp_cd: dict[tuple[int,int], int] = {}
        self.hunger_tick.start()

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""
            PRAGMA journal_mode=WAL;
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
    def _cd_ok(self, gid: int, uid: int, key: str, sec: int) -> bool:
        now = int(dt.datetime.utcnow().timestamp())
        until = self.cooldowns.get((gid, uid, key), 0)
        if until > now:
            return False
        self.cooldowns[(gid, uid, key)] = now + sec
        return True

    def _sentiment(self, text: str) -> Optional[str]:
        neg = sum(1 for w in NEG_WORDS if w in text)
        pos = sum(1 for w in POS_WORDS if w in text)
        if neg - pos >= 2:
            return "neg"
        if pos - neg >= 2:
            return "pos"
        return None

    async def _get_user(self, gid: int, uid: int):
        async with aiosqlite.connect(DB_PATH) as db:
            row = await (await db.execute(
                "SELECT pet_name, pet_lv, pet_xp, pet_hunger, coins FROM users WHERE guild_id=? AND user_id=?",
                (gid, uid)
            )).fetchone()
            if row:
                return {"pet_name": row[0], "pet_lv": row[1], "pet_xp": row[2], "pet_hunger": row[3], "coins": row[4]}
            await db.execute("INSERT INTO users (guild_id, user_id, coins) VALUES (?,?,0)", (gid, uid))
            await db.commit()
            return {"pet_name": None, "pet_lv": 1, "pet_xp": 0, "pet_hunger": 0, "coins": 0}

    async def _add_xp(self, gid: int, uid: int, xp: int = 1) -> Tuple[int,int]:
        async with aiosqlite.connect(DB_PATH) as db:
            row = await (await db.execute(
                "SELECT pet_lv, pet_xp FROM users WHERE guild_id=? AND user_id=?",
                (gid, uid)
            )).fetchone()
            if not row:
                pet_lv, pet_xp = 1, 0
                await db.execute("INSERT INTO users (guild_id, user_id, pet_lv, pet_xp) VALUES (?,?,?,?)",
                                 (gid, uid, pet_lv, pet_xp))
            else:
                pet_lv, pet_xp = row
            pet_xp += xp
            while pet_xp >= 10 * pet_lv:
                pet_xp -= 10 * pet_lv
                pet_lv += 1
            await db.execute("UPDATE users SET pet_lv=?, pet_xp=? WHERE guild_id=? AND user_id=?",
                             (pet_lv, pet_xp, gid, uid))
            await db.commit()
            return pet_lv, pet_xp

    async def _get_daily(self, gid: int, uid: int):
        key = taipei_today_key()
        async with aiosqlite.connect(DB_PATH) as db:
            row = await (await db.execute(
                "SELECT challenge, completed, reward FROM daily WHERE guild_id=? AND user_id=? AND date_key=?",
                (gid, uid, key)
            )).fetchone()
            if row:
                return {"challenge": row[0], "completed": int(row[1]), "reward": int(row[2])}
            challenge = random.choice(DAILY_POOL)
            reward = random.randint(5, 15)
            await db.execute("INSERT INTO daily (guild_id,user_id,date_key,challenge,reward) VALUES (?,?,?,?,?)",
                             (gid, uid, key, challenge, reward))
            await db.commit()
            return {"challenge": challenge, "completed": 0, "reward": reward}

    async def _complete_daily(self, gid: int, uid: int) -> Tuple[bool,int]:
        key = taipei_today_key()
        async with aiosqlite.connect(DB_PATH) as db:
            row = await (await db.execute(
                "SELECT completed, reward FROM daily WHERE guild_id=? AND user_id=? AND date_key=?",
                (gid, uid, key)
            )).fetchone()
            if not row or row[0]:
                return False, 0
            reward = int(row[1])
            await db.execute("UPDATE daily SET completed=1 WHERE guild_id=? AND user_id=? AND date_key=?",
                             (gid, uid, key))
            await db.execute("UPDATE users SET coins = COALESCE(coins,0) + ? WHERE guild_id=? AND user_id=?",
                             (reward, gid, uid))
            await db.commit()
            return True, reward

    # ────────── on_message：彩蛋 / 情緒 / XP & 轉交指令 ──────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        gid, uid, content = message.guild.id, message.author.id, message.content

        # 彩蛋（每人每鍵 10 秒冷卻）
        for key, replies in EGG_TRIGGERS.items():
            if key in content and self._cd_ok(gid, uid, f"egg:{key}", 10):
                await message.channel.send(random.choice(replies))
                break

        # 情緒偵測（30 秒冷卻）
        senti = self._sentiment(content)
        if senti and self._cd_ok(gid, uid, f"senti:{senti}", 30):
            if senti == "neg":
                await message.channel.send(f"{message.author.mention} 抱一個 🤗 要不要抽張 `!tarot`？")
            else:
                await message.channel.send(f"{message.author.mention} 能量滿滿！分享今天一件開心的小事吧～")

        # 聊天給 XP（每 10 秒一次）
        now = int(dt.datetime.utcnow().timestamp())
        if self.xp_cd.get((gid, uid), 0) <= now:
            await self._get_user(gid, uid)
            await self._add_xp(gid, uid, xp=1)
            self.xp_cd[(gid, uid)] = now + 10

        # ⬅️ 關鍵：把訊息交給指令解析器（避免吃掉指令）
        await self.bot.process_commands(message)

    # ────────── 指令：寵物 ──────────
    @commands.command(name="adopt")
    async def adopt(self, ctx: commands.Context, *, pet_name: str):
        """收養寵物：!adopt 皮蛋"""
        data = await self._get_user(ctx.guild.id, ctx.author.id)
        if data["pet_name"]:
            return await ctx.reply(f"你已經有寵物 **{data['pet_name']}** 啦！")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET pet_name=? WHERE guild_id=? AND user_id=?",
                             (pet_name, ctx.guild.id, ctx.author.id))
            await db.commit()
        await ctx.reply(f"🎉 恭喜收養 **{pet_name}** ！好好照顧牠～")

    @commands.command(name="pet")
    async def pet_profile(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """查看寵物資訊：!pet 或 !pet @某人"""
        m = member or ctx.author
        d = await self._get_user(ctx.guild.id, m.id)
        if not d["pet_name"]:
            return await ctx.reply(f"{m.display_name} 還沒有寵物，使用 `!adopt 名字` 來收養吧！")
        await ctx.reply(
            f"**{m.display_name}** 的寵物 **{d['pet_name']}**\n"
            f"等級：{d['pet_lv']} ｜ 經驗：{d['pet_xp']}/{10*d['pet_lv']}\n"
            f"飢餓：{d['pet_hunger']} ｜ 金幣：{d['coins']}"
        )

    @commands.command(name="feed")
    async def feed(self, ctx: commands.Context):
        """餵食寵物：!feed（降飢餓 + 小量 XP）"""
        d = await self._get_user(ctx.guild.id, ctx.author.id)
        if not d["pet_name"]:
            return await ctx.reply("你還沒有寵物，先 `!adopt 名字` 吧！")
        async with aiosqlite.connect(DB_PATH) as db:
            hunger = max(0, int(d["pet_hunger"] or 0) - 2)
            await db.execute("UPDATE users SET pet_hunger=? WHERE guild_id=? AND user_id=?",
                             (hunger, ctx.guild.id, ctx.author.id))
            await db.commit()
        lv, xp = await self._add_xp(ctx.guild.id, ctx.author.id, xp=2)
        await ctx.reply(f"🍖 餵食完成！等級 {lv}，XP {xp}/{10*lv}")

    @commands.command(name="duel")
    async def duel(self, ctx: commands.Context, opponent: Optional[discord.Member]):
        """寵物對戰：!duel @對手（擲骰 + 等級）"""
        if not opponent or opponent.bot:
            return await ctx.reply("請 @ 一位對手（不能是機器人）")
        a = await self._get_user(ctx.guild.id, ctx.author.id)
        b = await self._get_user(ctx.guild.id, opponent.id)
        if not a["pet_name"] or not b["pet_name"]:
            return await ctx.reply("雙方都需要先有寵物（`!adopt`）才能對戰！")
        ra = random.randint(1, 6) + int(a["pet_lv"])
        rb = random.randint(1, 6) + int(b["pet_lv"])
        if ra > rb:
            await self._add_xp(ctx.guild.id, ctx.author.id, xp=3)
            return await ctx.reply(f"⚔️ {ctx.author.display_name} 擲出 {ra}，擊敗 {opponent.display_name} 的 {rb}！")
        if rb > ra:
            await self._add_xp(ctx.guild.id, opponent.id, xp=3)
            return await ctx.reply(f"⚔️ {opponent.display_name} 擲出 {rb}，擊敗 {ctx.author.display_name} 的 {ra}！")
        return await ctx.reply("平手！再來一場～")

    # ────────── 指令：每日任務 ──────────
    @commands.command(name="daily")
    async def daily(self, ctx: commands.Context):
        """查看/領取今日任務：!daily"""
        d = await self._get_daily(ctx.guild.id, ctx.author.id)
        status = "✅ 已完成" if d["completed"] else "⏳ 未完成"
        await ctx.reply(
            f"📅 今日任務：**{d['challenge']}**\n"
            f"獎勵：{d['reward']} 金幣\n"
            f"狀態：{status}\n"
            f"完成後輸入 `!done` 領獎。"
        )

    @commands.command(name="done")
    async def done(self, ctx: commands.Context):
        """完成任務領獎：!done"""
        ok, reward = await self._complete_daily(ctx.guild.id, ctx.author.id)
        if not ok:
            return await ctx.reply("今天沒有任務或已領過獎勵。輸入 `!daily` 查看。")
        await ctx.reply(f"🎁 任務完成！獲得 **{reward}** 金幣！")

    # ────────── 指令：趣味工具 ──────────
    @commands.command(name="tarot")
    async def tarot(self, ctx: commands.Context):
        """抽一張塔羅：!tarot"""
        await ctx.reply(f"🔮 你的牌：**{random.choice(TAROT)}**")

    @commands.command(name="meme")
    async def meme(self, ctx: commands.Context, *, text: str = ""):
        """
        梗圖生成：上傳圖片 + !meme 上面字|下面字
        只想一段文字就寫在前面即可（可留空）。
        """
        if not ctx.message.attachments:
            return await ctx.reply("請附上一張圖片再下指令（上傳一張圖 + `!meme 上面字|下面字`）")
        top, bottom = "", ""
        if "|" in text:
            top, bottom = [s.strip() for s in text.split("|", 1)]
        else:
            top = text.strip()
        attach = ctx.message.attachments[0]
        data = await attach.read()
        base = Image.open(io.BytesIO(data))
        out = draw_meme(base, top=top, bottom=bottom)
        buf = io.BytesIO()
        out.save(buf, format="JPEG", quality=92)
        buf.seek(0)
        await ctx.reply(file=discord.File(buf, filename="meme.jpg"))

    @commands.command(name="cp")
    async def cp(self, ctx: commands.Context, role: Optional[discord.Role] = None):
        """
        隨機 CP 配對：!cp 或 !cp @某身分組
        從伺服器成員（或指定身分組）中抽兩位，排除機器人與自己。
        """
        if role:
            pool = [m for m in role.members if not m.bot and m != ctx.author]
        else:
            pool = [m for m in ctx.guild.members if not m.bot and m != ctx.author]
        if len(pool) < 2:
            return await ctx.reply("可配對的人太少啦～再等等人多一點！")
        a, b = random.sample(pool, 2)
        await ctx.reply(f"💘 今日緣分是：**{a.display_name}** × **{b.display_name}** ！")

    # ────────── 定時任務：每小時飢餓 +1（最大 10） ──────────
    @tasks.loop(minutes=60)
    async def hunger_tick(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET pet_hunger = MIN(10, COALESCE(pet_hunger,0) + 1)")
            await db.commit()

    @hunger_tick.before_loop
    async def _before_tick(self):
        await self.bot.wait_until_ready()

# ────────── Extension 載入點 ──────────
async def setup(bot: commands.Bot):
    await bot.add_cog(FunSuite(bot))
