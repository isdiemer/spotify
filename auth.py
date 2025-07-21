import base64, secrets, time, urllib.parse as up
from os import getenv
from pathlib import Path

import requests
from flask import Flask, redirect, render_template, request, session, url_for

from token_store import FileTokenStore, TokenBundle   # <- your token_store.py

# ─── config ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key   = getenv("FLASK_SECRET_KEY")            # 32-byte random str
TOKEN_KEY  = "spotify_tokens"        
CLIENT_ID        = getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET    = getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI     = getenv("SPOTIFY_REDIRECT_URI")        # e.g. https://localhost:5000/callback
SCOPE            = (
    "user-read-private user-read-email user-library-read user-library-modify "
    "playlist-read-private playlist-modify-public playlist-modify-private"
)

# single source-of-truth for tokens
STORE = FileTokenStore(Path("tokens.json"))

# ─── low-level helpers ─────────────────────────────────────────────────────
def _post_token(data: dict) -> dict:
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        data=data,
        headers={"Authorization": f"Basic {auth}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()

def _exchange_code(code: str) -> None:
    tok = _post_token(
        {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI}
    )
    _save_bundle(tok)

def _refresh(refresh_token: str) -> TokenBundle:
    tok = _post_token({"grant_type": "refresh_token", "refresh_token": refresh_token})
    return _save_bundle(tok)

def _save_bundle(tok_json: dict) -> TokenBundle:
    bundle: TokenBundle = {
        "access_token": tok_json["access_token"],
        "refresh_token": tok_json.get("refresh_token")      # may be absent on refresh
                        or STORE.get()["refresh_token"],
        "expires_at": int(time.time() + tok_json["expires_in"]),
    }
    STORE.set(TOKEN_KEY,bundle)
    return bundle

def _get_valid_token() -> str:
    bundle = STORE.get(TOKEN_KEY)
    if not bundle:
        raise RuntimeError("User not authenticated yet.")
    if time.time() >= bundle["expires_at"] - 30:
        bundle = _refresh(bundle["refresh_token"])
    return bundle["access_token"]

# ─── routes ────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    logged_in = STORE.get(TOKEN_KEY) is not None
    return render_template("index.html", logged_in=logged_in)

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
    _exchange_code(code)                          # tokens stored via STORE.save
    return redirect(url_for("index"))

@app.route("/profile")
def profile():
    """Get current user’s Spotify profile."""
    try:
        token = _get_valid_token()
    except RuntimeError:
        return redirect(url_for("login"))

    r = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code == 401:                      # reactive fallback
        bundle = STORE.get(TOKEN_KEY)
        token  = _refresh(bundle["refresh_token"])["access_token"]
        r = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    r.raise_for_status()
    return r.json()

@app.route("/debug/refresh")
def debug_refresh():
    """Force a refresh for dev testing."""
    bundle = STORE.get(TOKEN_KEY)
    if not bundle:
        return "Not logged in.", 401
    new = _refresh(bundle["refresh_token"])
    return {
        "msg": "Access token refreshed immediately",
        "expires_in": int(new["expires_at"] - time.time()),
    }

# ─── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
