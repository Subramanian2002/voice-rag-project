import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


WHISPER_MODEL = "whisper-large-v3"


TRANSCRIPTION_PROMPT = (
    "Transcribe the user's speech accurately. "
    "Preserve proper nouns, people's names, company names, "
    "organization names, product names, technical terms, "
    "abbreviations, numbers, dates, titles, and other "
    "domain-specific terminology. "
    "If a word is unfamiliar, preserve the spoken word "
    "rather than replacing it with a more common "
    "similar-sounding word. "
    "Maintain the intended wording and meaning "
    "of the user's speech."
)


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "recording.webm"
) -> str:

    """
    Convert recorded audio into text using
    Groq Whisper.
    """

    if not audio_bytes:
        raise ValueError(
            "No audio data received."
        )

    transcription = (
        groq_client.audio.transcriptions.create(

            file=(
                filename,
                audio_bytes
            ),

            model=WHISPER_MODEL,

            language="en",

            prompt=TRANSCRIPTION_PROMPT,

            response_format="json",

            temperature=0
        )
    )

    text = (
        transcription.text
        if transcription.text
        else ""
    )

    return text.strip()