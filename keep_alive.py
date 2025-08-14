from flask import Flask, request, render_template_string, redirect
from threading import Thread
import json
import os

app = Flask('')

@app.route('/')
def home():
    # 如果 config.json 不存在，先建立一個空的
    if not os.path.exists('config.json'):
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump({}, f)

    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    html = f"""
    <h1>Bot 設定</h1>
    <form action="/save" method="post">
        Prefix: <input type="text" name="prefix" value="{config.get('prefix', '')}"><br>
        歡迎頻道ID: <input type="text" name="welcome_channel_id" value="{config.get('welcome_channel_id', '')}"><br>
        歡迎訊息: <input type="text" name="welcome_message" value="{config.get('welcome_message', '')}"><br>
        <input type="submit" value="儲存">
    </form>
    """
    return render_template_string(html)

@app.route('/save', methods=['POST'])
def save():
    new_config = {
        "prefix": request.form.get('prefix', ''),
        "welcome_channel_id": int(request.form.get('welcome_channel_id', '0') or 0),
        "welcome_message": request.form.get('welcome_message', '')
    }
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)
    return redirect('/')

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
