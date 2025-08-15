from flask import Flask, request, render_template_string, redirect
import json
import os
from threading import Thread
import config_manager  

app = Flask(__name__)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    # 每次載入頁面都重新讀取最新設定
    config = config_manager.load_config()

    if request.method == "POST":
        new_data = {
            "prefix": request.form.get("prefix", config.get("prefix", "!")),
            "welcome_channel_id": int(request.form.get("welcome_channel_id", config.get("welcome_channel_id", 0))),
            "welcome_message": request.form.get("welcome_message", config.get("welcome_message", ""))
        }
        config_manager.save_config(new_data)  # 即時寫入
        return redirect("/settings")

    html = """
    <h1>Bot 設定</h1>
    <form method="POST">
        Prefix: <input type="text" name="prefix" value="{{prefix}}"><br><br>
        歡迎頻道ID: <input type="text" name="welcome_channel_id" value="{{welcome_channel_id}}"><br><br>
        歡迎訊息: <textarea name="welcome_message">{{welcome_message}}</textarea><br><br>
        <input type="submit" value="儲存">
    </form>
    """
    return render_template_string(html,
                                  prefix=config.get("prefix", "!"),
                                  welcome_channel_id=config.get("welcome_channel_id", 0),
                                  welcome_message=config.get("welcome_message", ""))

@app.route("/")
def home():
    return "Bot 後台運作中 🚀"

def keep_alive():
    def run():
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)

    t = Thread(target=run)
    t.start()
