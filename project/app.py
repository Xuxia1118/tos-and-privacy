from flask import Flask, render_template, redirect, request, session
import os
import requests

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "devkey")

# Discord OAuth2 設定
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/callback")
API_BASE = "https://discord.com/api"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    return redirect(
        f"{API_BASE}/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code&scope=identify%20guilds"
    )

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided", 400

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(f"{API_BASE}/oauth2/token", data=data, headers=headers)
    r.raise_for_status()
    creds = r.json()
    session["token"] = creds["access_token"]

    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    if "token" not in session:
        return redirect("/login")
    headers = {"Authorization": f"Bearer {session['token']}"}
    r = requests.get(f"{API_BASE}/users/@me/guilds", headers=headers)
    guilds = r.json()
    return render_template("dashboard.html", guilds=guilds)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
