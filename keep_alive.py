
# keep_alive.py
import os
import json
from threading import Thread
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from flask import Flask, redirect, request, session, url_for, render_template_string
import config_manager  # 你的設定檔管理器

# ──────────────────────────────────────────────────────────
# Flask APP
# ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

# Discord OAuth2 相關設定
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "")
OAUTH_SCOPE = "identify guilds email"

DISCORD_API_BASE = "https://discord.com/channels/@me"

# ──────────────────────────────────────────────────────────
# 小工具：HTTP 請求
# ──────────────────────────────────────────────────────────
def post_form(url: str, data: dict) -> dict:
    body = urlencode(data).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": f"HTTPError {e.code}", "details": e.read().decode("utf-8", "ignore")}
    except URLError as e:
        return {"error": "URLError", "details": str(e)}

def get_json(url: str, headers: dict) -> dict:
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": f"HTTPError {e.code}", "details": e.read().decode("utf-8", "ignore")}
    except URLError as e:
        return {"error": "URLError", "details": str(e)}

# ──────────────────────────────────────────────────────────
# 路由
# ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "discord_user" in session:
        user = session["discord_user"]
        avatar_hash = user.get("avatar")
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar_hash}.png"
            if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"
        )
        return f"""
        <h1>歡迎，{user.get('username')}#{user.get('discriminator', '0000')}</h1>
        <img src="{avatar_url}" width="96" height="96" style="border-radius:50%"><br><br>
        <a href="/settings">前往設定頁</a> |
        <a href="/guilds">查看伺服器清單</a> |
        <a href="/logout">登出</a>
        """
    return """
    <h1>Bot 後台</h1>
    <p>請先登入 Discord 以管理設定。</p>
    <a href="/login">使用 Discord 登入</a>
    """

@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/login")
def login():
    if not (CLIENT_ID and REDIRECT_URI):
        return "尚未設定 DISCORD_CLIENT_ID / DISCORD_REDIRECT_URI", 500

    # 保留原始 scope 讓 urlencode 自動轉成 %20
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": OAUTH_SCOPE
    }
    auth_url = f"{DISCORD_API_BASE}/oauth2/authorize?{urlencode(params)}"
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "缺少授權碼（code）", 400

    if not (CLIENT_ID and CLIENT_SECRET and REDIRECT_URI):
        return "尚未設定 DISCORD_CLIENT_ID / DISCORD_CLIENT_SECRET / DISCORD_REDIRECT_URI", 500

    # 用 code 換取 token（scope 參數移除）
    token_resp = post_form(
        f"{DISCORD_API_BASE}/oauth2/token",
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
    )

    print("Token response:", token_resp)  # debug log

    access_token = token_resp.get("access_token")
    if not access_token:
        return f"授權失敗：{token_resp}", 400

    # 拿使用者資訊
    user = get_json(
        f"{DISCORD_API_BASE}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if "id" not in user:
        return f"取得使用者資料失敗：{user}", 400

    session["discord_user"] = user
    session["access_token"] = access_token
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("discord_user", None)
    session.pop("access_token", None)
    return redirect(url_for("index"))

@app.route("/guilds")
def guilds():
    if "access_token" not in session:
        return redirect(url_for("login"))

    guilds = get_json(
        f"{DISCORD_API_BASE}/users/@me/guilds",
        headers={"Authorization": f"Bearer {session['access_token']}"}
    )
    if isinstance(guilds, dict) and "error" in guilds:
        return f"取得伺服器失敗：{guilds}", 400

    items = []
    for g in guilds:
        name = g.get("name", "Unknown")
        gid = g.get("id")
        perm = g.get("permissions", 0)
        items.append(f"<li>{name} (ID: {gid}) — perms: {perm}</li>")
    return "<h1>你的伺服器</h1><ul>" + "".join(items) + "</ul><a href='/'>返回</a>"

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "discord_user" not in session:
        return redirect(url_for("login"))

    config = config_manager.load_config()

    if request.method == "POST":
        new_data = {
            "prefix": (request.form.get("prefix") or config.get("prefix", "!")).strip(),
            "welcome_channel_id": int(request.form.get("welcome_channel_id") or config.get("welcome_channel_id", 0)),
            "welcome_message": (request.form.get("welcome_message") or config.get("welcome_message", "")).strip(),
        }
        config_manager.save_config(new_data)
        return redirect(url_for("settings"))

    html = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<title>Bot 設定頁</title>
<style>
body { font-family: ui-sans-serif, system-ui; padding: 24px; }
.card { max-width: 680px; margin: 0 auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 12px; }
label { display:block; margin:.5rem 0 .25rem; font-weight:600; }
input[type="text"], textarea { width:100%; padding:.6rem .8rem; border:1px solid #d1d5db; border-radius:8px; }
button { margin-top:1rem; padding:.6rem 1rem; border:0; border-radius:10px; cursor:pointer; }
.primary { background:#111827; color:white; }
.row { display:grid; gap:12px; }
a { color:#2563eb; text-decoration:none; }
</style>
</head>
<body>
<div class="card">
<h1>Bot 設定</h1>
<form method="POST" class="row">
<div><label>Prefix</label><input type="text" name="prefix" value="{{prefix}}"></div>
<div><label>歡迎頻道 ID</label><input type="text" name="welcome_channel_id" value="{{welcome_channel_id}}"></div>
<div><label>歡迎訊息（支援 {{ '{user}' }} 變數）</label><textarea name="welcome_message" rows="4">{{welcome_message}}</textarea></div>
<button class="primary" type="submit">儲存設定</button>
</form>
<p style="margin-top:1rem;"><a href="/">返回首頁</a></p>
</div>
</body>
</html>"""
    return render_template_string(
        html,
        prefix=config.get("prefix", "!"),
        welcome_channel_id=config.get("welcome_channel_id", 0),
        welcome_message=config.get("welcome_message", "")
    )

# ──────────────────────────────────────────────────────────
# 啟動 Flask
# ──────────────────────────────────────────────────────────
def keep_alive():
    def run():
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port, debug=False)
    Thread(target=run, daemon=True).start()
