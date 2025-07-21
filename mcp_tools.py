from fastmcp import FastMCP     
import os 
from typing import Any
from spotify_client import SpotifyClient
from token_store import FileTokenStore, TokenBundle
mcp = FastMCP("spotify")

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
STORE = FileTokenStore("tokens.json")


@mcp.tool()
def get_playing() -> Any:
    """
    Get the currently playing track on Spotify.
    """
    client = SpotifyClient(CLIENT_ID, CLIENT_SECRET, STORE)
    return client.get_playing()
    
if __name__ == "__main__":
    mcp.run()
