from hashlib import sha256

from app.extractors import extract_pdf_text, extract_txt_text, extract_pptx_text
from app.chunker import chunk_text
from app.embeddings import generate_embedding
from app.qdrant_db import store_embedding, search_embeddings, source_exists
from app.llm import generate_answer_with_fallback


# ============================================================
# SOURCE ID
# ============================================================

def make_url_source_id(url: str) -> str:
    normalized_url = str(url or "").strip().rstrip("/").lower()
    return sha256(normalized_url.encode("utf-8")).hexdigest()


# ============================================================
# FILE TEXT EXTRACTION
# ============================================================

def extract_file_text(source: dict) -> str:
    file_path = source["file_path"]
    source_type = source["source_type"]

    if source_type == "pdf":
        return extract_pdf_text(file_path)

    if source_type == "txt":
        return extract_txt_text(file_path)

    if source_type == "pptx":
        return extract_pptx_text(file_path)

    raise ValueError(f"Unsupported source type: {source_type}")


# ============================================================
# PROCESS FILE
# ============================================================

def process_file(source: dict) -> list[str]:
    text = extract_file_text(source)

    if not text or not text.strip():
        raise ValueError(f"No text found in {source['source_name']}")

    chunks = chunk_text(text)

    if not chunks:
        raise ValueError(f"No chunks generated for {source['source_name']}")

    return chunks


# ============================================================
# GENERATE EMBEDDINGS
# ============================================================

def embed_chunks(chunks: list[str]) -> list[list[float]]:
    embeddings = []

    for chunk in chunks:
        if not chunk or not chunk.strip():
            continue

        vector = generate_embedding(chunk)

        if not vector:
            raise ValueError("Failed to generate embedding.")

        embeddings.append(vector)

    if not embeddings:
        raise ValueError("No embeddings were generated.")

    return embeddings


# ============================================================
# STORE CHUNKS
# ============================================================

def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    source: dict,
    session_id: str
):
    if len(chunks) != len(embeddings):
        raise ValueError("Number of chunks and embeddings does not match.")

    source_id = str(source.get("source_id", "")).strip()

    if not source_id:
        raise ValueError(
            f"Source ID is missing for {source.get('source_name', 'unknown source')}"
        )

    for chunk, vector in zip(chunks, embeddings):
        metadata = {
            "source_id": source_id,
            "source_type": source.get("source_type"),
            "source_name": source.get("source_name"),
            "source_url": source.get("source_url"),
            "session_id": session_id
        }

        store_embedding(
            vector=vector,
            text=chunk,
            metadata=metadata
        )


# ============================================================
# PROCESS FILE SOURCE
# ============================================================

def process_source(source: dict, session_id: str) -> int:
    chunks = process_file(source)
    embeddings = embed_chunks(chunks)

    store_chunks(
        chunks=chunks,
        embeddings=embeddings,
        source=source,
        session_id=session_id
    )

    return len(chunks)


# ============================================================
# PROCESS URL SOURCE
# ============================================================

def process_url(source: dict, session_id: str) -> int:
    text = source.get("text", "")
    url = source.get("url", "").strip()

    if not text or not text.strip():
        raise ValueError(f"No text found for URL: {url}")

    chunks = chunk_text(text)

    if not chunks:
        raise ValueError(f"No chunks generated for URL: {url}")

    embeddings = embed_chunks(chunks)

    source_id = source.get("source_id") or make_url_source_id(url)

    source_metadata = {
        "source_id": source_id,
        "source_type": "url",
        "source_name": url,
        "source_url": url
    }

    store_chunks(
        chunks=chunks,
        embeddings=embeddings,
        source=source_metadata,
        session_id=session_id
    )

    return len(chunks)


# ============================================================
# PROCESS ALL CURRENT SESSION SOURCES
# ============================================================

def process_all_sources(
    uploaded_sources: list,
    url_sources: list,
    session_id: str
):
    total_files = 0
    total_urls = 0
    total_files_skipped = 0
    total_urls_skipped = 0
    total_chunks = 0

    # --------------------------------------------------------
    # FILES
    # --------------------------------------------------------

    unique_files = []
    seen_file_ids = set()

    for source in uploaded_sources:
        source_id = str(
            source.get("source_id") or source.get("file_hash") or ""
        ).strip()

        if not source_id:
            raise ValueError(
                f"Source ID is missing for {source.get('source_name', 'unknown file')}"
            )

        source["source_id"] = source_id

        if source_id in seen_file_ids:
            total_files_skipped += 1
            print(
                f"Skipping duplicate file in session: "
                f"{source.get('source_name', source_id)}"
            )
            continue

        seen_file_ids.add(source_id)
        unique_files.append(source)

    for source in unique_files:
        source_id = source["source_id"]

        if source_exists(
            session_id=session_id,
            source_id=source_id
        ):
            total_files_skipped += 1
            print(
                f"Skipping already processed file: "
                f"{source.get('source_name', source_id)}"
            )
            continue

        chunks = process_source(
            source=source,
            session_id=session_id
        )

        total_files += 1
        total_chunks += chunks

        print(
            f"Processed file: "
            f"{source.get('source_name', source_id)} "
            f"({chunks} chunks)"
        )

    # --------------------------------------------------------
    # URLS
    # --------------------------------------------------------

    unique_urls = []
    seen_url_ids = set()

    for source in url_sources:
        url = source.get("url", "").strip()

        if not url:
            continue

        source_id = str(
            source.get("source_id") or make_url_source_id(url)
        ).strip()

        source["source_id"] = source_id

        if source_id in seen_url_ids:
            total_urls_skipped += 1
            print(f"Skipping duplicate URL: {url}")
            continue

        seen_url_ids.add(source_id)
        unique_urls.append(source)

    for source in unique_urls:
        url = source["url"]
        source_id = source["source_id"]

        if source_exists(
            session_id=session_id,
            source_id=source_id
        ):
            total_urls_skipped += 1
            print(f"Skipping already processed URL: {url}")
            continue

        chunks = process_url(
            source=source,
            session_id=session_id
        )

        total_urls += 1
        total_chunks += chunks

        print(
            f"Processed URL: {url} ({chunks} chunks)"
        )

    return {
        "files_processed": total_files,
        "files_skipped": total_files_skipped,
        "urls_processed": total_urls,
        "urls_skipped": total_urls_skipped,
        "chunks_stored": total_chunks
    }


# ============================================================
# BUILD RAG CONTEXT
# ============================================================

def build_context(results) -> str:
    context_parts = []

    for result in results:
        payload = result.payload or {}
        text = payload.get("text", "")

        if text:
            context_parts.append(text)

    return "\n\n---\n\n".join(context_parts)


# ============================================================
# BUILD CONVERSATION HISTORY
# ============================================================

def build_conversation_history(
    conversation_history: list[dict] | None
) -> str:
    if not conversation_history:
        return ""

    history_parts = []

    for message in conversation_history:
        role = message.get("role", "")
        content = message.get("content", "")

        if not content:
            continue

        content = str(content).strip()

        if not content:
            continue

        if role == "user":
            history_parts.append(f"User: {content}")

        elif role == "assistant":
            history_parts.append(f"Assistant: {content}")

    return "\n\n".join(history_parts)


# ============================================================
# BUILD SOURCES
# ============================================================

def build_sources(results) -> list[dict]:
    sources = []

    for result in results:
        payload = result.payload or {}

        source = {
            "source_type": payload.get("source_type"),
            "source_name": payload.get("source_name"),
            "source_url": payload.get("source_url")
        }

        if source not in sources:
            sources.append(source)

    return sources


# ============================================================
# ANSWER QUESTION
# ============================================================

def answer_question(
    question: str,
    conversation_history: list[dict] | None = None,
    limit: int = 5,
    session_id: str = ""
):
    question = question.strip()

    if not question:
        return {
            "answer": "Please ask a question.",
            "sources": []
        }

    if not session_id:
        return {
            "answer": (
                "I could not find that information "
                "in the provided sources."
            ),
            "sources": []
        }

    # Generate query embedding.
    query_vector = generate_embedding(question)

    if not query_vector:
        raise ValueError("Failed to generate query embedding.")

    # Search ONLY inside the current session.
    results = search_embeddings(
        query_vector=query_vector,
        limit=limit,
        session_id=session_id
    )

    if not results:
        return {
            "answer": (
                "I could not find that information "
                "in the provided sources."
            ),
            "sources": []
        }

    # Build RAG context.
    context = build_context(results)

    if not context.strip():
        return {
            "answer": (
                "I could not find that information "
                "in the provided sources."
            ),
            "sources": []
        }

    # Build conversation history.
    history_text = build_conversation_history(
        conversation_history
    )

    # Generate answer.
    answer = generate_answer_with_fallback(
        context=context,
        question=question,
        conversation_history=history_text
    )

    # Build source list.
    sources = build_sources(results)

    return {
        "answer": answer,
        "sources": sources
    }