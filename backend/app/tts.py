import edge_tts


DEFAULT_VOICE = "en-US-GuyNeural"



async def generate_speech(
    text: str,
    output_file: str,
    voice: str = DEFAULT_VOICE
):
    """
    Convert text into speech using Edge TTS.

    Args:
        text: Text to speak.
        output_file: Path where MP3 will be saved.
        voice: Edge TTS voice name.
    """

    if not text or not text.strip():
        raise ValueError(
            "Text cannot be empty."
        )


    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="+0%",
        volume="+0%"
    )


    await communicate.save(
        output_file
    )


    return output_file