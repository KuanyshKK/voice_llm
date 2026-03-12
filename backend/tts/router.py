from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from .elevenlabs_tts import text_to_speech, text_to_speech_stream

router = APIRouter(prefix="/tts", tags=["TTS"])


class TTSRequest(BaseModel):
    text: str


@router.post("/synthesize")
async def synthesize(request: TTSRequest):
    """
    POST /tts/synthesize
    Body: {"text": "Привет, вот мероприятия на сегодня..."}
    Returns: аудио файл mp3
    """
    audio_bytes = text_to_speech(request.text)
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=response.mp3"},
    )


@router.post("/synthesize-stream")
async def synthesize_stream(request: TTSRequest):
    """
    Стриминговый эндпоинт (бонус).
    Фронтенд получает аудио чанками и начинает играть сразу.
    """
    audio_stream = text_to_speech_stream(request.text)
    return StreamingResponse(
        audio_stream,
        media_type="audio/mpeg",
    )