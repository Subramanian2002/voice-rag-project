import os
import tempfile
import uuid

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Header
)

from pydantic import (
    BaseModel,
    Field
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

from fastapi.responses import (
    FileResponse
)

from app.scraper import (
    scrape_url
)

from app.sources import (
    uploaded_sources,
    url_sources
)

from app.processor import (
    process_all_sources,
    answer_question
)

from app.speech import (
    transcribe_audio
)

from app.tts import (
    generate_speech
)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="QUiRRI RAG API",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    FRONTEND_URL
]

ALLOWED_ORIGINS = list(
    dict.fromkeys(
        ALLOWED_ORIGINS
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# UPLOAD CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".pptx"
}


# ============================================================
# SESSION VALIDATION
# ============================================================

def validate_session_id(
    session_id: str
) -> str:

    if session_id is None:

        raise HTTPException(
            status_code=400,
            detail=(
                "X-Session-ID header "
                "is required."
            )
        )

    session_id = session_id.strip()

    if not session_id:

        raise HTTPException(
            status_code=400,
            detail=(
                "Session ID cannot "
                "be empty."
            )
        )

    if len(session_id) > 200:

        raise HTTPException(
            status_code=400,
            detail="Invalid session ID."
        )

    return session_id


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy"
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "message":
            "QUiRRI RAG API is running",

        "status":
            "healthy"
    }


# ============================================================
# FILE UPLOAD
# ============================================================

@app.post("/upload")
async def upload_files(

    files: list[UploadFile] = File(...),

    session_id: str = Header(
        ...,
        alias="X-Session-ID"
    )
):

    session_id = validate_session_id(
        session_id
    )

    if not files:

        raise HTTPException(
            status_code=400,
            detail=(
                "Please select at least "
                "one file."
            )
        )

    if session_id not in uploaded_sources:

        uploaded_sources[
            session_id
        ] = []

    uploaded_files = []

    for file in files:

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail=(
                    "File name is missing."
                )
            )

        original_filename = os.path.basename(
            file.filename
        )

        file_extension = os.path.splitext(
            original_filename
        )[1].lower()

        if (
            file_extension
            not in ALLOWED_EXTENSIONS
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported file type: "
                    f"{original_filename}. "
                    f"Supported types: "
                    f"PDF, TXT and PPTX."
                )
            )

        safe_filename = (
            f"{uuid.uuid4().hex}_"
            f"{original_filename}"
        )

        file_path = os.path.join(
            UPLOAD_DIR,
            safe_filename
        )

        try:

            file_content = (
                await file.read()
            )

            if not file_content:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"File is empty: "
                        f"{original_filename}"
                    )
                )

            with open(
                file_path,
                "wb"
            ) as buffer:

                buffer.write(
                    file_content
                )

        except HTTPException:

            raise

        except Exception as e:

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to save "
                    f"{original_filename}: "
                    f"{str(e)}"
                )
            )

        finally:

            await file.close()

        uploaded_sources[
            session_id
        ].append(
            {
                "file_path":
                    file_path,

                "source_name":
                    original_filename,

                "source_type":
                    file_extension.lstrip("."),

                "session_id":
                    session_id
            }
        )

        uploaded_files.append(
            original_filename
        )

    return {
        "message":
            "Files uploaded successfully",

        "files":
            uploaded_files
    }


# ============================================================
# URL REQUEST MODEL
# ============================================================

class URLRequest(
    BaseModel
):

    url: str


# ============================================================
# ADD WEBSITE URL
# ============================================================

@app.post("/add-url")
def add_url(

    request: URLRequest,

    session_id: str = Header(
        ...,
        alias="X-Session-ID"
    )
):

    session_id = validate_session_id(
        session_id
    )

    url = request.url.strip()

    if not url:

        raise HTTPException(
            status_code=400,
            detail="URL cannot be empty."
        )

    if session_id not in url_sources:

        url_sources[
            session_id
        ] = []

    normalized_current_url = (
        url
        .strip()
        .rstrip("/")
        .lower()
    )

    for source in url_sources[
        session_id
    ]:

        existing_url = (
            source.get(
                "url",
                ""
            )
            .strip()
            .rstrip("/")
            .lower()
        )

        if (
            existing_url
            == normalized_current_url
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "This URL has "
                    "already been added."
                )
            )

    try:

        print(
            f"Scraping URL: {url}"
        )

        text = scrape_url(
            url
        )

        if not text or not text.strip():

            raise HTTPException(
                status_code=400,
                detail=(
                    "The webpage did not "
                    "contain readable content."
                )
            )

        url_sources[
            session_id
        ].append(
            {
                "url":
                    url,

                "text":
                    text,

                "source_type":
                    "url",

                "session_id":
                    session_id
            }
        )

        print(
            f"URL scraped successfully: "
            f"{url}"
        )

        return {
            "message":
                "URL scraped successfully",

            "source_url":
                url
        }

    except HTTPException:

        raise

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


# ============================================================
# PROCESS SOURCES
# ============================================================

@app.post("/process")
def process_sources(

    session_id: str = Header(
        ...,
        alias="X-Session-ID"
    )
):

    session_id = validate_session_id(
        session_id
    )

    try:

        session_uploaded_sources = (
            uploaded_sources.get(
                session_id,
                []
            )
        )

        session_url_sources = (
            url_sources.get(
                session_id,
                []
            )
        )

        print(
            "================================"
        )

        print(
            "Processing session:",
            session_id
        )

        print(
            "Files:",
            len(
                session_uploaded_sources
            )
        )

        print(
            "URLs:",
            len(
                session_url_sources
            )
        )

        print(
            "================================"
        )

        if (
            not session_uploaded_sources
            and
            not session_url_sources
        ):

            return {
                "message":
                    "No sources found "
                    "for this session.",

                "files_processed":
                    0,

                "urls_processed":
                    0,

                "chunks_stored":
                    0
            }

        result = process_all_sources(
            uploaded_sources=
                session_uploaded_sources,

            url_sources=
                session_url_sources,

            session_id=
                session_id
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


# ============================================================
# ASK REQUEST MODEL
# ============================================================

class AskRequest(
    BaseModel
):

    question: str

    conversation_history: list[dict] = Field(
        default_factory=list
    )


# ============================================================
# ASK QUESTION
# ============================================================

@app.post("/ask")
def ask_question(

    request: AskRequest,

    session_id: str = Header(
        ...,
        alias="X-Session-ID"
    )
):

    session_id = validate_session_id(
        session_id
    )

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail=(
                "Question cannot be empty."
            )
        )

    try:

        session_uploaded_sources = (
            uploaded_sources.get(
                session_id,
                []
            )
        )

        session_url_sources = (
            url_sources.get(
                session_id,
                []
            )
        )

        print(
            "================================"
        )

        print(
            f"Session: {session_id}"
        )

        print(
            f"Question: {question}"
        )

        print(
            "Current files:",
            len(
                session_uploaded_sources
            )
        )

        print(
            "Current URLs:",
            len(
                session_url_sources
            )
        )

        print(
            "Conversation history:",
            len(
                request.conversation_history
            )
        )

        print(
            "================================"
        )

        # IMPORTANT:
        # Never search Qdrant when the current session
        # has no active sources.
        #
        # Qdrant is persistent, while uploaded_sources
        # and url_sources are in-memory. Therefore old
        # vectors can exist even when the current session
        # has no current sources.

        if (
            not session_uploaded_sources
            and
            not session_url_sources
        ):

            return {
                "answer":
                    "I could not find that information "
                    "in the provided sources.",

                "sources":
                    []
            }

        result = answer_question(
            question=
                question,

            conversation_history=
                request.conversation_history,

            session_id=
                session_id
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


# ============================================================
# TRANSCRIBE VOICE
# ============================================================

@app.post("/transcribe")
async def transcribe_voice(

    audio: UploadFile = File(...)
):

    try:

        audio_bytes = (
            await audio.read()
        )

        if not audio_bytes:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No audio data received."
                )
            )

        filename = (
            audio.filename
            or
            "recording.webm"
        )

        print(
            f"Received audio: "
            f"{filename} "
            f"({len(audio_bytes)} bytes)"
        )

        text = transcribe_audio(
            audio_bytes=
                audio_bytes,

            filename=
                filename
        )

        text = text.strip()

        if not text:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not understand "
                    "the recorded audio."
                )
            )

        print(
            f"Transcription: {text}"
        )

        return {
            "text":
                text
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


# ============================================================
# TTS REQUEST MODEL
# ============================================================

class TTSRequest(
    BaseModel
):

    text: str


# ============================================================
# TEXT TO SPEECH
# ============================================================

@app.post("/tts")
async def text_to_speech(

    request: TTSRequest
):

    text = request.text.strip()

    if not text:

        raise HTTPException(
            status_code=400,
            detail=(
                "Text cannot be empty."
            )
        )

    temp_file = None

    try:

        temp_file = (
            tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".mp3"
            )
        )

        output_path = (
            temp_file.name
        )

        temp_file.close()

        await generate_speech(
            text=text,
            output_file=
                output_path
        )

        return FileResponse(
            output_path,
            media_type=
                "audio/mpeg",
            filename=
                "answer.mp3"
        )

    except Exception as e:

        if (
            temp_file
            and
            os.path.exists(
                temp_file.name
            )
        ):

            try:

                os.remove(
                    temp_file.name
                )

            except Exception:

                pass

        print(
            "TTS error:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "TTS generation failed: "
                f"{str(e)}"
            )
        )