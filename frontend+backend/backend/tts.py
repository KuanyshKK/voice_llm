import os
import httpx
from openai import AsyncOpenAI


async def synthesize_speech(text: str) -> bytes:
    # Try ElevenLabs first, fall back to OpenAI TTS
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    if elevenlabs_key:
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": elevenlabs_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
            )
            resp.raise_for_status()
            return resp.content
    else:
        # Fallback: OpenAI TTS
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = await client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text,
        )
        return response.content
