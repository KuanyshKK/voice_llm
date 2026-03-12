import os
import base64
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file (look one level up from backend/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from asr import transcribe_audio
from tts import synthesize_speech
from agent import run_agent

app = FastAPI(title="Voice AI Assistant", version="1.0.0")

# CORS — allow all origins so the browser frontend can reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/voice")
async def voice_pipeline(audio: UploadFile = File(...)):
    """
    Full pipeline:
        1. ASR  — Whisper transcribes the uploaded audio
        2. Agent — LangChain/OpenAI generates a response
        3. TTS  — ElevenLabs/OpenAI synthesises speech
    Returns JSON: { transcript, response_text, audio (base64 mp3) }
    """
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file received")

        # 1. ASR
        transcript = await transcribe_audio(audio_bytes, audio.filename or "recording.webm")

        if not transcript.strip():
            raise HTTPException(status_code=422, detail="Could not transcribe audio — please speak clearly")

        # 2. Agent
        response_text = await run_agent(transcript)

        # 3. TTS
        audio_data = await synthesize_speech(response_text)

        # Encode audio as base64 for JSON transport
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

        return JSONResponse(
            content={
                "transcript": transcript,
                "response_text": response_text,
                "audio": audio_b64,
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        print(f"[voice_pipeline] Unexpected error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# Mount the frontend as static files — must be done after API routes
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists() and frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
