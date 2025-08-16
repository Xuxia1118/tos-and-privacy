from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Hello! This is the landing page."

@app.route("/tos")
def tos():
    return "📄 Terms of Service page."

@app.route("/privacy")
def privacy():
    return "🔒 Privacy Policy page."

@app.route("/callback")
def callback():
    return "🔑 OAuth callback received."
