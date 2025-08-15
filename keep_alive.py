# keep_alive.py
from flask import Flask, request, render_template_string, redirect
import os
from threading import Thread
import config_manager  

app = Flask(__name__)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    config = config_manager.load_config()

    if request.method == "POST":
        # 防止輸入空值覆蓋設定
        new_data = {
            "prefix": request.form.get("prefix", config.get("prefix", "!")).strip(),
            "welcome_channel_id": int(request.form.get("welcome_channel_id", config.get("welcome_channel_id", 0))),
            "welcome_message": request.form.get("welcome_message", config.get("welcome_message", "")).strip()
        }
        config_manager.save_config(new_data)
        return redirect("/settings")

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Bot 設定頁面</title>
    </head>
    <body>
        <h1>Bot 設定</h1>
        <form method="POST">
            Prefix: <input type="text" name="prefix" value="{{prefix}}"><br><br>
            歡迎頻道ID: <input type="text" name="welcome_channel_id" value="{{welcome_channel_id}}"><br><br>
            歡迎訊息: <textarea name="welcome_message" rows="4" cols="40">{{welcome_message}}</textarea><br><br>
            <input type="submit" value="儲存">
        </form>
        <br>
        <a href="/">回首頁</a>
    </body>
    </html>
    """
    return render_template_string(
        html,
        prefix=config.get("prefix", "!"),
        welcome_channel_id=config.get("welcome_channel_id", 0),
        welcome_message=config.get("welcome_message", "")
    )

@app.route("/")
def home():
    return """
    <h1>Bot 後台運作中 🚀</h1>
    <p><a href='/settings'>前往設定頁面</a></p>
    """

def keep_alive():
    def run():
        port = int(os.environ.get("PORT", 8080))  # Railway 會自動設定 PORT
        app.run(host="0.0.0.0", port=port, debug=False)

    Thread(target=run).start()
