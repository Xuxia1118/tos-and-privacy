from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>機器人設定網站</h1><p>這裡以後可以加設定功能</p>"

def run_web():
    app.run(host="0.0.0.0", port=8080)
