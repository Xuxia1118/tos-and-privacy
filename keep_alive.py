from flask import Flask, request, render_template_string, redirect
from threading import Thread
import json

app = Flask('')

@app.route('/')
def home():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    html = f"""
    <h1>Bot 設定</h1>
    <form action="/save" method="post">
        Prefix: <input type="text" name="prefix" value="{config['prefix']}"><br>
        歡迎頻道ID: <input type="text" name="welcome_channel_id" value="{config['welcome_channel_id']}"><br>
        歡迎訊息: <input type="text" name="welcome_message" value="{config['welcome_message']}"><br>
        <input type="submit" value="儲存">
    </form>
    """
    return render_template_string(html)

@app.route('/save', methods=['POST'])
def save():
    new_config = {
        "prefix": request.form['prefix'],
        "welcome_channel_id": int(request.form['welcome_channel_id']),
        "welcome_message": request.form['welcome_message']
    }
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)
    return redirect('/')

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
