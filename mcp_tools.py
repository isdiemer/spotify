from fastmcp import FastMCP     
import os 
from typing import Any
from spotify_client import SpotifyClient
from pathlib import Path
from token_store import FileTokenStore, TokenBundle
mcp = FastMCP("spotify")

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
STORE = FileTokenStore(Path("tokens.json"))



@mcp.tool()
def get_playing() -> Any:
    """
    Get the currently playing track on Spotify.
    """
    # Ensure CLIENT_ID and CLIENT_SECRET are not None before passing to SpotifyClient
    if CLIENT_ID is None or CLIENT_SECRET is None or STORE is None:
        raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in environment variables.")

    client = SpotifyClient(CLIENT_ID, CLIENT_SECRET, STORE)
    return client.get_playing()
    
if __name__ == "__main__":
    mcp.run(transport="http", port=3333, host = "0.0.0.0")
