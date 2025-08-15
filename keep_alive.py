from flask import Flask, redirect, request, session, url_for
import os
import requests
from threading import Thread

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 必須有 secret_key 才能用 session

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
OAUTH_SCOPE = "identify guilds"

@app.route("/")
def index():
    if "discord_user" in session:
        user = session["discord_user"]
        return f"""
        <h1>歡迎, {user['username']}#{user['discriminator']}</h1>
        <img src="https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" width="100"><br>
        <a href="/logout">登出</a>
        """
    return '<a href="/login">使用 Discord 登入</a>'

@app.route("/login")
def login():
    return redirect(
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={OAUTH_SCOPE}"
    )

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "沒有授權碼", 400

    # 換取 access token
    token_url = "https://discord.com/api/oauth2/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": OAUTH_SCOPE
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_response = requests.post(token_url, data=data, headers=headers)
    token_json = token_response.json()
    access_token = token_json.get("access_token")

    if not access_token:
        return f"授權失敗: {token_json}", 400

    # 取得使用者資料
    user_info = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    session["discord_user"] = user_info
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("discord_user", None)
    return redirect(url_for("index"))

def keep_alive():
    def run():
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)
    Thread(target=run).start()
