import os
import discord
from discord.ext import commands
from flask import Flask, render_template_string, request
import threading

# 讀取 TOKEN（Railway 環境變數）
TOKEN = os.getenv("TOKEN")

# Discord Bot 初始化
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 防迴圈用的訊息 ID
last_message_id = None

# Flask 初始化
app = Flask(__name__)

# 配置檔（記憶功能設定）
config = {
    "reply_channel_id": None,
    "reply_text": "預設回覆"
}

# Flask 後台頁面 HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bot 設定</title>
</head>
<body>
    <h1>Bot 設定</h1>
    <form method="POST">
        <label>回覆頻道 ID:</label>
        <input type="text" name="channel_id" value="{{channel_id}}"><br><br>
        <label>回覆內容:</label>
        <input type="text" name="reply_text" value="{{reply_text}}"><br><br>
        <input type="submit" value="儲存">
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        config["reply_channel_id"] = int(request.form["channel_id"])
        config["reply_text"] = request.form["reply_text"]
        return "設定已更新"
    return render_template_string(
        HTML_TEMPLATE,
        channel_id=config["reply_channel_id"] or "",
        reply_text=config["reply_text"]
    )

# Discord Bot 事件
@bot.event
async def on_ready():
    print(f"Bot 已啟動：{bot.user}")

@bot.event
async def on_message(message):
    global last_message_id

    if message.author == bot.user:
        return
    if message.id == last_message_id:
        return
    if config["reply_channel_id"] and message.channel.id == config["reply_channel_id"]:
        await message.channel.send(config["reply_text"])
        last_message_id = message.id

    await bot.process_commands(message)

# 啟動 Flask + Discord
if __name__ == "__main__":
    def run_flask():
        port = int(os.environ.get("PORT", 8080))  # Railway 分配的 Port
        app.run(host="0.0.0.0", port=port)

    threading.Thread(target=run_flask).start()
    bot.run(TOKEN)
