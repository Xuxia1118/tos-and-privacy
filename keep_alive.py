from flask import Flask, request, render_template_string, redirect
import json
import os
from threading import Thread

app = Flask(__name__)

# 設定頁面
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        new_data = {
            "prefix": request.form.get("prefix", config_manager.config_data["prefix"]),
            "welcome_channel_id": int(request.form.get("welcome_channel_id", config_manager.config_data["welcome_channel_id"])),
            "welcome_message": request.form.get("welcome_message", config_manager.config_data["welcome_message"])
        }
        config_manager.update_config(new_data)
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
                                  prefix=config_manager.config_data["prefix"],
                                  welcome_channel_id=config_manager.config_data["welcome_channel_id"],
                                  welcome_message=config_manager.config_data["welcome_message"])

@app.route("/")
def home():
    return "Bot 後台運作中 🚀"

def keep_alive():
    def run():
        port = int(os.environ.get("PORT", 8080))  # Railway 要讀取 PORT
        app.run(host="0.0.0.0", port=port)

    t = Thread(target=run)
    t.start()
