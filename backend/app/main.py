from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

import os
import tempfile

from pydantic import BaseModel, Field

from fastapi.openapi.utils import get_openapi

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import FileResponse

# PROJECT IMPORTS
from app.scraper import scrape_url

from app.sources import (
    uploaded_sources,
    url_sources
)

from app.processor import (
    process_all_sources,
    answer_question
)

from app.speech import transcribe_audio

from app.tts import generate_speech



# FASTAPI APP

app = FastAPI()



# CORS
app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)





UPLOAD_DIR = "uploads"

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".pptx"
}

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)



# HEALTH CHECK


@app.get("/health")
def health_check():

    return {
        "status": "healthy"
    }



# FILE UPLOAD


@app.post("/upload")
async def upload_files(
    files: list[UploadFile] = File(...)
):

    uploaded_files = []

    for file in files:

        
        # Validate filename
        

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail="File name is missing."
            )

        
        # Get extension
        

        file_extension = os.path.splitext(
            file.filename
        )[1].lower()

        
        # Validate extension
        
        if (
            file_extension
            not in ALLOWED_EXTENSIONS
        ):

            raise HTTPException(
                status_code=400,

                detail=(
                    f"Unsupported file type: "
                    f"{file.filename}"
                )
            )

        
        # Save file
        

        file_path = os.path.join(
            UPLOAD_DIR,
            file.filename
        )

        try:

            file_content = await file.read()

            with open(
                file_path,
                "wb"
            ) as buffer:

                buffer.write(
                    file_content
                )

        except Exception as e:

            raise HTTPException(
                status_code=500,

                detail=(
                    f"Failed to save "
                    f"{file.filename}: {str(e)}"
                )
            )

        
        # Store source metadata
        

        uploaded_sources.append(
            {
                "file_path": file_path,

                "source_name":
                    file.filename,

                "source_type":
                    file_extension.lstrip(".")
            }
        )

        uploaded_files.append(
            file.filename
        )

    return {
        "message":
            "Files uploaded successfully",

        "files":
            uploaded_files
    }


# URL REQUEST MODEL

class URLRequest(BaseModel):

    url: str



# ADD WEBSITE URL

@app.post("/add-url")
def add_url(
    request: URLRequest
):

    url = request.url.strip()

    
    # Validate empty URL
    

    if not url:

        raise HTTPException(
            status_code=400,
            detail="URL cannot be empty."
        )

    try:

        print(
            f"Scraping URL: {url}"
        )

        #Scrape website
        
        text = scrape_url(
            url
        )

        
        # Store URL source
        
        url_sources.append(
            {
                "url": url,

                "text": text,

                "source_type": "url"
            }
        )

        print(
            f"URL scraped successfully: {url}"
        )

        return {
            "message":
                "URL scraped successfully",

            "source_url":
                url,

            "text":
                text
        }

    except ValueError as e:

        print(
            f"URL scraping error: {e}"
        )

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        print(
            f"Unexpected URL error: {e}"
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "Failed to process URL: "
                f"{str(e)}"
            )
        )



# PROCESS SOURCES


@app.post("/process")
def process_sources():

    try:

        result = process_all_sources(
            uploaded_sources=
                uploaded_sources,

            url_sources=
                url_sources
        )

        return {
            "message":
                "Sources processed successfully",

            **result
        }

    except Exception as e:

        print(
            "Source processing error:",
            e
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "Source processing failed: "
                f"{str(e)}"
            )
        )



# ASK REQUEST MODEL

class AskRequest(BaseModel):

    question: str

    conversation_history: list[dict] = Field(
        default_factory=list
    )



# ASK QUESTION


@app.post("/ask")
def ask_question(
    request: AskRequest
):

    question = request.question.strip()

    
    # Validate question
   
    if not question:

        raise HTTPException(
            status_code=400,

            detail="Question cannot be empty."
        )

    try:

        print(
            f"Question: {question}"
        )

        print(
            "Conversation history length:",
            len(
                request.conversation_history
            )
        )

        
        # RAG
        

        result = answer_question(
            question=question,

            conversation_history=
                request.conversation_history
        )

        return result

    except Exception as e:

        print(
            "Question answering error:",
            e
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "Failed to generate answer: "
                f"{str(e)}"
            )
        )



# TRANSCRIBE VOICE


@app.post("/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...)
):

    try:

        
        # Read audio
        

        audio_bytes = await audio.read()

        
        # Validate audio
        

        if not audio_bytes:

            raise HTTPException(
                status_code=400,

                detail=
                    "No audio data received."
            )

        # Log
        print(
            f"Received audio: "
            f"{audio.filename} "
            f"({len(audio_bytes)} bytes)"
        )

        
        # Whisper
        text = transcribe_audio(
            audio_bytes=audio_bytes,

            filename=(
                audio.filename
                or "recording.wav"
            )
        )

        print(
            f"Transcription: {text}"
        )

        return {
            "text": text
        }

    except HTTPException:

        raise

    except Exception as e:

        print(
            "Transcription error:",
            str(e)
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "Transcription failed: "
                f"{str(e)}"
            )
        )



# TTS REQUEST MODEL

class TTSRequest(BaseModel):

    text: str



# TEXT TO SPEECH

@app.post("/tts")
async def text_to_speech(
    request: TTSRequest
):

    text = request.text.strip()

    
    # Validate
    
    if not text:

        raise HTTPException(
            status_code=400,

            detail=
                "Text cannot be empty."
        )

    # Temporary MP3
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,

        suffix=".mp3"
    )

    output_path = temp_file.name

    temp_file.close()

    try:
        
        # Generate speech
        await generate_speech(
            text=text,

            output_file=output_path
        )

        
        # Return MP3
        return FileResponse(
            output_path,

            media_type="audio/mpeg",

            filename="answer.mp3"
        )

    except Exception as e:

        
        # Delete failed file
        if os.path.exists(
            output_path
        ):

            os.remove(
                output_path
            )

        print(
            "TTS error:",
            e
        )

        raise HTTPException(
            status_code=500,

            detail=(
                f"TTS generation failed: "
                f"{str(e)}"
            )
        )