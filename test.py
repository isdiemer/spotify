from http import client
import openai, os


openai.api_key = os.getenv("OPENAI_API_KEY")
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "get currently playing song"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_currently_playing_song",
            "description": "Get the currently playing song from Spotify.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }]
)
print(response)

