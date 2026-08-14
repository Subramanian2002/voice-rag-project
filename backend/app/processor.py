from app.extractors import (
    extract_pdf_text,
    extract_txt_text,
    extract_pptx_text
)

from app.chunker import (
    chunk_text
)

from app.embeddings import (
    generate_embedding
)

from app.qdrant_db import (
    store_embedding,
    search_embeddings
)

from app.llm import (
    generate_answer_with_fallback
)



# FILE TEXT EXTRACTION
def extract_file_text(
    source: dict
) -> str:

    file_path = source[
        "file_path"
    ]

    source_type = source[
        "source_type"
    ]

    if source_type == "pdf":

        return extract_pdf_text(
            file_path
        )

    if source_type == "txt":

        return extract_txt_text(
            file_path
        )

    if source_type == "pptx":

        return extract_pptx_text(
            file_path
        )

    raise ValueError(
        f"Unsupported source type: "
        f"{source_type}"
    )



# PROCESS FILE


def process_file(
    source: dict
) -> list[str]:

    text = extract_file_text(
        source
    )

    if not text.strip():

        raise ValueError(
            f"No text found in "
            f"{source['source_name']}"
        )

    chunks = chunk_text(
        text
    )

    if not chunks:

        raise ValueError(
            f"No chunks generated for "
            f"{source['source_name']}"
        )

    return chunks



# EMBEDDING


def embed_chunks(
    chunks: list[str]
) -> list[list[float]]:

    embeddings = []

    for chunk in chunks:

        vector = generate_embedding(
            chunk
        )

        embeddings.append(
            vector
        )

    return embeddings



# STORE CHUNKS
def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    source: dict
):

    for chunk, vector in zip(
        chunks,
        embeddings
    ):

        metadata = {

            "source_type":
                source["source_type"],

            "source_name":
                source["source_name"],

            "source_url":
                source.get("source_url")
        }

        store_embedding(
            vector=vector,

            text=chunk,

            metadata=metadata
        )



# PROCESS FILE SOURCE

def process_source(
    source: dict
):

    chunks = process_file(
        source
    )

    embeddings = embed_chunks(
        chunks
    )

    store_chunks(
        chunks=chunks,

        embeddings=embeddings,

        source=source
    )

    return len(chunks)



# PROCESS URL SOURCE

def process_url(
    source: dict
):

    text = source[
        "text"
    ]

    if not text.strip():

        raise ValueError(
            f"No text found for URL: "
            f"{source['url']}"
        )

    chunks = chunk_text(
        text
    )

    if not chunks:

        raise ValueError(
            f"No chunks generated for URL: "
            f"{source['url']}"
        )

    embeddings = embed_chunks(
        chunks
    )

    source_metadata = {

        "source_type":
            "url",

        "source_name":
            source["url"],

        "source_url":
            source["url"]
    }

    store_chunks(
        chunks=chunks,

        embeddings=embeddings,

        source=source_metadata
    )

    return len(chunks)



# PROCESS ALL SOURCES

def process_all_sources(
    uploaded_sources: list,
    url_sources: list
):

    total_files = 0

    total_urls = 0

    total_chunks = 0


    
    for source in uploaded_sources:

        chunks = process_source(
            source
        )

        total_files += 1

        total_chunks += chunks


    
    # URLs
    

    for source in url_sources:

        chunks = process_url(
            source
        )

        total_urls += 1

        total_chunks += chunks


    return {

        "files_processed":
            total_files,

        "urls_processed":
            total_urls,

        "chunks_stored":
            total_chunks
    }



# BUILD RAG CONTEXT

def build_context(
    results
) -> str:

    context_parts = []

    for result in results:

        text = result.payload.get(
            "text",
            ""
        )

        if text:

            context_parts.append(
                text
            )

    return "\n\n---\n\n".join(
        context_parts
    )


# BUILD CONVERSATION HISTORY
def build_conversation_history(
    conversation_history:
        list[dict] | None
) -> str:

    if not conversation_history:

        return ""


    history_parts = []


    for message in conversation_history:

        role = message.get(
            "role",
            ""
        )

        content = message.get(
            "content",
            ""
        )


        if not content:

            continue


        content = str(
            content
        ).strip()


        if not content:

            continue


        if role == "user":

            history_parts.append(
                f"User: {content}"
            )


        elif role == "assistant":

            history_parts.append(
                f"Assistant: {content}"
            )


    return "\n\n".join(
        history_parts
    )



# ANSWER QUESTION

def answer_question(
    question: str,

    conversation_history:
        list[dict] | None = None,

    limit: int = 5
):

    question = question.strip()


    if not question:

        return {

            "answer":
                "Please ask a question.",

            "sources": []
        }


    
    # Generate query embedding
   
    query_vector = generate_embedding(
        question
    )


    # Search Qdrant
    
    results = search_embeddings(
        query_vector=query_vector,

        limit=limit
    )
    if not results:

        return {

            "answer":
                "I could not find that information "
                "in the provided sources.",

            "sources": []
        }


    
    # Build context
    
    context = build_context(
        results
    )


    
    # Build conversation history
    
    history_text = (
        build_conversation_history(
            conversation_history
        )
    )


    
    # Generate answer
    
    answer = generate_answer_with_fallback(

        context=context,

        question=question,

        conversation_history=
            history_text
    )


    sources = []


    for result in results:

        payload = (
            result.payload
        )


        source = {

            "source_type":
                payload.get(
                    "source_type"
                ),

            "source_name":
                payload.get(
                    "source_name"
                ),

            "source_url":
                payload.get(
                    "source_url"
                )
        }


        if source not in sources:

            sources.append(
                source
            )


    return {

        "answer":
            answer,

        "sources":
            sources
    }