import json
import os
import typer
import openai
from pathlib import Path
from typing import Any

from spotify_client import SpotifyClient
from token_store import FileTokenStore

app = typer.Typer(help="Interact with Spotify via natural language")


def get_currently_playing_song() -> Any:
    """Return the user's currently playing song from Spotify."""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set"
        )
    store = FileTokenStore(Path("tokens.json"))
    client = SpotifyClient(client_id, client_secret, store)
    return client.get_playing()


def search_tracks(query: str, limit: int = 5) -> Any:
    """Search for tracks on Spotify matching QUERY."""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set"
        )
    store = FileTokenStore(Path("tokens.json"))
    client = SpotifyClient(client_id, client_secret, store)
    return client.search_tracks(query, limit=limit)


def get_track(track_id: str) -> Any:
    """Fetch a track by its Spotify ID."""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set"
        )
    store = FileTokenStore(Path("tokens.json"))
    client = SpotifyClient(client_id, client_secret, store)
    return client.get_track(track_id)


def run_conversation(prompt: str) -> str:
    """Send a prompt to OpenAI and handle any tool calls."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY must be set")
    openai.api_key = api_key

    messages = [
        {"role": "user", "content": prompt}
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_currently_playing_song",
                "description": "Get the currently playing song from Spotify.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_tracks",
                "description": "Search for tracks by query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search keywords"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_track",
                "description": "Look up a track by its Spotify ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "track_id": {"type": "string", "description": "Spotify track ID"},
                    },
                    "required": ["track_id"],
                },
            },
        },
    ]

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
    )

    message = response.choices[0].message
    messages.append(message)

    if message.tool_calls:
        for call in message.tool_calls:
            if call.function.name == "get_currently_playing_song":
                result = get_currently_playing_song()
                messages.append(
                    {
                        "tool_call_id": call.id,
                        "role": "tool",
                        "name": call.function.name,
                        "content": json.dumps(result),
                    }
                )
            elif call.function.name == "search_tracks":
                args = json.loads(call.function.arguments)
                result = search_tracks(args.get("query"), limit=args.get("limit", 5))
                messages.append(
                    {
                        "tool_call_id": call.id,
                        "role": "tool",
                        "name": call.function.name,
                        "content": json.dumps(result),
                    }
                )
            elif call.function.name == "get_track":
                args = json.loads(call.function.arguments)
                result = get_track(args.get("track_id"))
                messages.append(
                    {
                        "tool_call_id": call.id,
                        "role": "tool",
                        "name": call.function.name,
                        "content": json.dumps(result),
                    }
                )
        followup = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        return followup.choices[0].message.content or ""
    return message.content or ""


@app.command()
def chat(prompt: str) -> None:
    """Send PROMPT to the assistant and print the response."""
    result = run_conversation(prompt)
    print(result)


if __name__ == "__main__":
    app()
