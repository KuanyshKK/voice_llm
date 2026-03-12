import os
import io
from openai import AsyncOpenAI


async def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # needed for format detection
    transcript = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="ru",  # primary language is Russian
    )
    return transcript.text
