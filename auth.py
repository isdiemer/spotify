import base64, secrets
import urllib.parse as up
from os import getenv

import requests
from flask import Flask, redirect, request, session, url_for, render_template

app = Flask(__name__)
app.secret_key = getenv("FLASK_SECRET_KEY")  # random 32-byte string in .env

CLIENT_ID       = getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET   = getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI    = getenv("SPOTIFY_REDIRECT_URI")          # e.g. https://localhost:5000/callback
SCOPE           = "user-read-private user-read-email user-library-read user-library-modify " \
                  "playlist-read-private playlist-modify-public playlist-modify-private"

# ---------- helpers ---------------------------------------------------------

def exchange_code_for_tokens(code: str) -> dict[str, str]:
    """Swap authorization code for {access,refresh}_token dict."""
    body = {
        "grant_type":    "authorization_code",
        "code":          code,
        "redirect_uri":  REDIRECT_URI,
    }
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        data=body,
        headers={"Authorization": f"Basic {auth_header}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()

def refresh_access_token(refresh_token: str) -> dict[str, str]:
    body = {
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
    }
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        data=body,
        headers={"Authorization": f"Basic {auth_header}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()

# ---------- routes ----------------------------------------------------------

@app.route("/")
def index():
    access_token = session.get("access_token")
    return render_template("index.html", logged_in=bool(access_token))

@app.route("/login")
def login():
    state = secrets.token_urlsafe(16)
    session["state"] = state
    params = dict(
        response_type="code",
        client_id=CLIENT_ID,
        scope=SCOPE,
        redirect_uri=REDIRECT_URI,
        state=state,
    )
    return redirect("https://accounts.spotify.com/authorize?" + up.urlencode(params))

@app.route("/callback")
def callback():
    if request.args.get("state") != session.pop("state", None):
        return "State mismatch. Possible CSRF.", 400

    code = request.args.get("code")
    if not code:
        return "No code supplied", 400

    tokens = exchange_code_for_tokens(code)
    session["access_token"]  = tokens["access_token"]
    session["refresh_token"] = tokens.get("refresh_token")  # present only on first grant
    session["expires_in"]    = tokens["expires_in"]         # 3600 seconds

    return redirect(url_for("index"))

# ---------- example protected request --------------------------------------

@app.route("/profile")
def profile():
    """Calls the 'Get Current User's Profile' endpoint."""
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("login"))

    r = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if r.status_code == 401:
        # Access token expired – refresh and retry once
        tokens = refresh_access_token(session["refresh_token"])
        session["access_token"] = tokens["access_token"]
        r = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {session['access_token']}"},
            timeout=10,
        )

    r.raise_for_status()
    return r.json()

@app.route("/debug/refresh")
def force_refresh():
    """Manually invoke the refresh-token flow for dev testing."""
    if "refresh_token" not in session:
        return "Not logged in or no refresh token stored.", 401

    tokens = refresh_access_token(session["refresh_token"])

    # Update session with the brand-new access token (+ any fields Spotify returns)
    session["access_token"] = tokens["access_token"]
    session["expires_in"]  = tokens["expires_in"]

    return {
        "msg":        "Access token refreshed immediately",
        "expires_in": tokens["expires_in"],
    }, 200
if __name__ == "__main__":
    app.run(debug=True, port=5000)
