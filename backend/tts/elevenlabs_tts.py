import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def text_to_speech(text: str) -> bytes:
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",        
        input=text,
    )
    return response.content


def text_to_speech_stream(text: str):
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
    )
    return iter([response.content])