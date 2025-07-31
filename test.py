import os
import json
import openai
from pathlib import Path
from token_store import FileTokenStore
from spotify_client import SpotifyClient

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
STORE = FileTokenStore(Path("tokens.json"))

def get_currently_playing_song():
    """Return the track currently playing on Spotify."""
    if CLIENT_ID is None or CLIENT_SECRET is None:
        raise RuntimeError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set")
    client = SpotifyClient(CLIENT_ID, CLIENT_SECRET, STORE)
    return client.get_playing()


api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable not set")
openai.api_key = api_key

messages = [{"role": "user", "content": "get currently playing song"}]
tools = [{
    "type": "function",
    "function": {
        "name": "get_currently_playing_song",
        "description": "Get the currently playing song from Spotify.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}]

while True:
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
    )
    msg = response.choices[0].message
    messages.append(msg)

    if not msg.tool_calls:
        print(msg.content)
        break

    for call in msg.tool_calls:
        if call.function.name == "get_currently_playing_song":
            result = get_currently_playing_song()
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": json.dumps(result),
            })


