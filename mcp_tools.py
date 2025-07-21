from FastMCP import MCPTools, FastMCP
import os 
from typing import Any


mcp = FastMCP("spotify")

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

@mcp.tool()
def get_playing() -> Any:
    """
    Get the currently playing track on Spotify.
    """
    