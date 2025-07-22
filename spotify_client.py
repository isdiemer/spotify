from __future__ import annotations
import time,json,base64,requests
from token_store import FileTokenStore, TokenBundle, TokenStore
from typing import Optional,Any, Dict


__all__ = ["SpotifyClient"]

_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SPOTIFY_API_ROOT = "https://api.spotify.com/v1"

class SpotifyClient:
    """ Wrapper around the Spotify API with token management. """
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        store: TokenStore,
        safety_margin: int = 30,
    ) -> None:
        self.id       = client_id
        self.secret   = client_secret
        self.store    = store
        self._margin  = safety_margin
        self._tokens: Optional[TokenBundle] = store.get("spotify_tokens")

    def _valid_token(self) -> str:
        if self._tokens is None or time.time() > self._tokens["expires_at"] - self._margin:
            self._refresh()
        return self._tokens["access_token"] if self._tokens else ""

    def _refresh(self) -> None:
        if self._tokens is None:
            raise RuntimeError("No refresh token available.")
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._tokens["refresh_token"],
            "client_id": self.id,
            "client_secret": self.secret,
        }
        r = requests.post(_SPOTIFY_TOKEN_URL, data=data, timeout=10)
        r.raise_for_status()
        resp = r.json()
        self._tokens["access_token"] = resp["access_token"]
        self._tokens["expires_at"] = time.time() + resp.get("expires_in", 3600)
        self.store.set("spotify_tokens", self._tokens)
    

    def _get(self, path: str, *, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, *, json: dict | None = None, params: dict | None = None) -> Any:
        return self._request("POST", path, json=json, params=params)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        token = self._valid_token()
        headers = kwargs.pop("headers", {}) | {"Authorization": f"Bearer {token}"}
        url = _SPOTIFY_API_ROOT + path

        r = requests.request(method, url, headers=headers, timeout=10, **kwargs)
        if r.status_code == 401:
            # reactive refresh then retry once
            self._refresh()
            if self._tokens is None:
                raise RuntimeError("Failed to refresh tokens.")
            headers["Authorization"] = f"Bearer {self._tokens['access_token']}"
            r = requests.request(method, url, headers=headers, timeout=10, **kwargs)
        r.raise_for_status()
        return r.json() if r.content else None

    def get_playing(self) -> Any:
        """
        Get the currently playing track on Spotify.
        """
        return self._get("/me/player/currently-playing")