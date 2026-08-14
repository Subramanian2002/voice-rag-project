import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

WHISPER_MODEL = "whisper-large-v3"


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "recording.webm"
) -> str:

    """
    Convert recorded audio into text using
    Groq Whisper.
    """

    transcription = groq_client.audio.transcriptions.create(
        file=(
            filename,
            audio_bytes
        ),
        model=WHISPER_MODEL,
        language="en",
        response_format="json",
        temperature=0
    )

    return transcription.text.strip()

