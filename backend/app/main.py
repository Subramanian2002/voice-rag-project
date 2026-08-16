import hashlib
import os
import tempfile
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.scraper import scrape_url,UnsupportedURL
from app.sources import uploaded_sources, url_sources
from app.processor import process_all_sources, answer_question
from app.speech import transcribe_audio
from app.tts import generate_speech
from app.qdrant_db import create_collection, delete_source_vectors


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

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

ALLOWED_ORIGINS = list(dict.fromkeys([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    FRONTEND_URL
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# QDRANT STARTUP
# ============================================================

@app.on_event("startup")
def initialize_qdrant():
    create_collection()


# ============================================================
# UPLOAD CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".pptx"
}


# ============================================================
# SESSION VALIDATION
# ============================================================

def validate_session_id(session_id: str) -> str:
    if session_id is None:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required."
        )

    session_id = session_id.strip()

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID cannot be empty."
        )

    if len(session_id) > 200:
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID."
        )

    return session_id


# ============================================================
# SOURCE ID
# ============================================================

def make_source_id(value: str) -> str:
    normalized = str(value or "").strip().rstrip("/").lower()

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "QUiRRI RAG API is running",
        "status": "healthy"
    }


# ============================================================
# FILE UPLOAD
# ============================================================

@app.post("/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    session_id: str = Header(..., alias="X-Session-ID")
):
    session_id = validate_session_id(session_id)

    if not files:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one file."
        )

    # Only sources belonging to the current browser session.
    session_sources = uploaded_sources.setdefault(session_id, [])

    new_files = []
    duplicate_files = []
    source_details = []

    for file in files:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="File name is missing."
            )

        original_filename = os.path.basename(file.filename)

        file_extension = os.path.splitext(original_filename)[1].lower()

        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported file type: {original_filename}. "
                    "Supported types: PDF, TXT and PPTX."
                )
            )

        try:
            file_content = await file.read()

            if not file_content:
                raise HTTPException(
                    status_code=400,
                    detail=f"File is empty: {original_filename}"
                )

            # SHA-256 identifies the actual file contents.
            file_hash = hashlib.sha256(file_content).hexdigest()

            # Check duplicate only inside the current session.
            duplicate = any(
                source.get("source_id") == file_hash
                or source.get("file_hash") == file_hash
                for source in session_sources
            )

            if duplicate:
                duplicate_files.append(original_filename)

                print(
                    "Duplicate upload skipped:",
                    original_filename
                )

                continue

            stored_filename = f"{uuid.uuid4().hex}_{original_filename}"

            file_path = os.path.join(
                UPLOAD_DIR,
                stored_filename
            )

            with open(file_path, "wb") as buffer:
                buffer.write(file_content)

            source = {
                "file_path": file_path,
                "source_name": original_filename,
                "source_type": file_extension.lstrip("."),
                "file_hash": file_hash,
                "source_id": file_hash,
                "session_id": session_id
            }

            session_sources.append(source)

            new_files.append(original_filename)

            source_details.append({
                "source_type": source["source_type"],
                "source_name": source["source_name"],
                "source_id": source["source_id"]
            })

        except HTTPException:
            raise

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save {original_filename}: {exc}"
            )

        finally:
            await file.close()

    if new_files and duplicate_files:
        message = (
            f"{len(new_files)} new file(s) uploaded. "
            f"{len(duplicate_files)} duplicate file(s) skipped."
        )
    elif new_files:
        message = f"{len(new_files)} new file(s) uploaded."
    elif duplicate_files:
        message = (
            f"{len(duplicate_files)} file(s) were already "
            "uploaded and were skipped."
        )
    else:
        message = "No new files were added."

    return {
        "message": message,
        "files": new_files,
        "new_files": new_files,
        "duplicate_files": duplicate_files,
        "sources": source_details
    }


# ============================================================
# URL REQUEST MODEL
# ============================================================

class URLRequest(BaseModel):
    url: str


# ============================================================
# ADD WEBSITE URL
# ============================================================

@app.post("/add-url")
def add_url(
    request: URLRequest,
    session_id: str = Header(..., alias="X-Session-ID")
):
    session_id = validate_session_id(session_id)

    url = request.url.strip()

    if not url:
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL. Please enter a valid website URL."
        )

    normalized_url = url.rstrip("/").lower()
    session_sources = url_sources.setdefault(session_id, [])

    for source in session_sources:
        existing_url = (
            source.get("url", "")
            .strip()
            .rstrip("/")
            .lower()
        )

        if existing_url == normalized_url:
            raise HTTPException(
                status_code=400,
                detail="This URL has already been added."
            )

    try:
        text = scrape_url(url)

        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="The webpage did not contain readable content."
            )

        source_id = make_source_id(normalized_url)

        source = {
            "url": url,
            "text": text,
            "source_type": "url",
            "source_name": url,
            "source_url": url,
            "source_id": source_id,
            "session_id": session_id
        }

        session_sources.append(source)

        return {
            "message": "URL scraped successfully",
            "source_url": url,
            "source_id": source_id
        }

    except UnsupportedURL as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process URL: {exc}"
        )

# ============================================================
# PROCESS SOURCES
# ============================================================

@app.post("/process")
def process_sources(
    session_id: str = Header(..., alias="X-Session-ID")
):
    session_id = validate_session_id(session_id)

    try:
        # Get sources ONLY from this current browser session.
        session_uploaded_sources = uploaded_sources.get(
            session_id,
            []
        )

        session_url_sources = url_sources.get(
            session_id,
            []
        )

        if not session_uploaded_sources and not session_url_sources:
            return {
                "message": "No sources found for this session.",
                "files_processed": 0,
                "files_skipped": 0,
                "urls_processed": 0,
                "urls_skipped": 0,
                "chunks_stored": 0
            }

        result = process_all_sources(
            uploaded_sources=session_uploaded_sources,
            url_sources=session_url_sources,
            session_id=session_id
        )

        return {
            "message": "Sources processed successfully",
            **result
        }

    except Exception as exc:
        print("Source processing error:", exc)

        raise HTTPException(
            status_code=500,
            detail=f"Source processing failed: {exc}"
        )


# ============================================================
# REMOVE SOURCE REQUEST
# ============================================================

class RemoveSourceRequest(BaseModel):
    source_type: str
    source_name: str


# ============================================================
# REMOVE SOURCE
# ============================================================

@app.delete("/remove-source")
def remove_source(
    request: RemoveSourceRequest,
    session_id: str = Header(..., alias="X-Session-ID")
):
    session_id = validate_session_id(session_id)

    source_type = request.source_type.strip().lower()
    source_name = request.source_name.strip()

    if not source_type or not source_name:
        raise HTTPException(
            status_code=400,
            detail="Source type and source name are required."
        )

    source_id = None
    removed_from_session = False

    # ========================================================
    # REMOVE URL
    # ========================================================

    if source_type == "url":
        current_sources = url_sources.get(session_id, [])
        remaining_sources = []

        requested_url = source_name.rstrip("/").lower()

        for source in current_sources:
            existing_url = (
                source.get("url", "")
                .strip()
                .rstrip("/")
                .lower()
            )

            if existing_url == requested_url:
                source_id = (
                    source.get("source_id")
                    or make_source_id(existing_url)
                )

                removed_from_session = True
                continue

            remaining_sources.append(source)

        url_sources[session_id] = remaining_sources

    # ========================================================
    # REMOVE FILE
    # ========================================================

    else:
        current_sources = uploaded_sources.get(session_id, [])
        remaining_sources = []

        for source in current_sources:
            if source.get("source_name") == source_name:
                source_id = (
                    source.get("source_id")
                    or source.get("file_hash")
                )

                removed_from_session = True

                file_path = source.get("file_path")

                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError as exc:
                        print(
                            "Could not remove local file:",
                            exc
                        )

                continue

            remaining_sources.append(source)

        uploaded_sources[session_id] = remaining_sources

    # ========================================================
    # DELETE QDRANT VECTORS
    # ========================================================

    if source_id:
        try:
            delete_source_vectors(
                session_id=session_id,
                source_id=source_id
            )

        except Exception as exc:
            print(
                "Qdrant source deletion error:",
                exc
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to remove source from "
                    f"vector database: {exc}"
                )
            )

    return {
        "message": (
            "Source removed successfully."
            if removed_from_session
            else "Source was not found in this session."
        ),
        "removed_from_session": removed_from_session,
        "source_type": source_type,
        "source_name": source_name,
        "source_id": source_id
    }


# ============================================================
# ASK REQUEST MODEL
# ============================================================

class AskRequest(BaseModel):
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
    session_id: str = Header(..., alias="X-Session-ID")
):
    session_id = validate_session_id(session_id)

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:
        # ====================================================
        # CURRENT SESSION SOURCES ONLY
        # ====================================================

        session_uploaded_sources = uploaded_sources.get(
            session_id,
            []
        )

        session_url_sources = url_sources.get(
            session_id,
            []
        )

        print("================================")
        print(f"Session: {session_id}")
        print(f"Question: {question}")
        print(
            "Current files:",
            len(session_uploaded_sources)
        )
        print(
            "Current URLs:",
            len(session_url_sources)
        )
        print(
            "Conversation history:",
            len(request.conversation_history)
        )
        print("================================")

        

        if not session_uploaded_sources and not session_url_sources:
            return {
                "answer": (
                    "I could not find that information "
                    "in the provided sources."
                ),
                "sources": []
            }

        result = answer_question(
            question=question,
            conversation_history=request.conversation_history,
            session_id=session_id
        )

        return result

    except Exception as exc:
        print("Question answering error:", exc)

        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate answer: {exc}"
        )


# ============================================================
# TRANSCRIBE VOICE
# ============================================================

@app.post("/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...)
):
    try:
        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="No audio data received."
            )

        filename = audio.filename or "recording.wav"

        print(
            f"Received audio: {filename} "
            f"({len(audio_bytes)} bytes)"
        )

        text = transcribe_audio(
            audio_bytes=audio_bytes,
            filename=filename
        )

        text = str(text or "").strip()

        if not text:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not understand "
                    "the recorded audio."
                )
            )

        print(f"Transcription: {text}")

        return {"text": text}

    except HTTPException:
        raise

    except Exception as exc:
        print("Transcription error:", exc)

        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {exc}"
        )


# ============================================================
# TTS REQUEST MODEL
# ============================================================

class TTSRequest(BaseModel):
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
            detail="Text cannot be empty."
        )

    temp_file = None

    try:
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3"
        )

        output_path = temp_file.name

        temp_file.close()

        await generate_speech(
            text=text,
            output_file=output_path
        )

        return FileResponse(
            output_path,
            media_type="audio/mpeg",
            filename="answer.mp3"
        )

    except Exception as exc:
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.remove(temp_file.name)
            except OSError:
                pass

        print("TTS error:", exc)

        raise HTTPException(
            status_code=500,
            detail=f"TTS generation failed: {exc}"
        )