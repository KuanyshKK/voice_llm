from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from asr.whisper_client import transcribe_audio
from tts.router import router as tts_router

app = FastAPI(title="Voice LLM - ASR Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tts_router)

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    text = transcribe_audio(audio_bytes, filename=file.filename)
    return {"text": text}
