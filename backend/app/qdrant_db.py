import os
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL:
    raise ValueError("QDRANT_URL is not configured.")


# ============================================================
# QDRANT CLIENT
# ============================================================

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

COLLECTION_NAME = "voice_rag_documents"

VECTOR_SIZE = 3072


# ============================================================
# CREATE COLLECTION
# ============================================================

def create_collection():
    collections = client.get_collections()

    existing_collections = {
        collection.name
        for collection in collections.collections
    }

    if COLLECTION_NAME not in existing_collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

        print(
            f"Collection '{COLLECTION_NAME}' created."
        )

    else:
        print(
            f"Collection '{COLLECTION_NAME}' already exists."
        )

    create_payload_indexes()


# ============================================================
# PAYLOAD INDEXES
# ============================================================

def create_payload_indexes():
    indexes = [
        ("session_id", PayloadSchemaType.KEYWORD),
        ("source_id", PayloadSchemaType.KEYWORD),
        ("source_type", PayloadSchemaType.KEYWORD)
    ]

    for field_name, field_schema in indexes:
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=field_schema,
                wait=True
            )

            print(
                f"Payload index ready: {field_name}"
            )

        except Exception as exc:
            error_message = str(exc).lower()

            if (
                "already exists" in error_message
                or "already exist" in error_message
            ):
                print(
                    f"Payload index already exists: {field_name}"
                )

            else:
                raise


# ============================================================
# SESSION FILTER
# ============================================================

def build_session_filter(session_id: str):
    session_id = str(session_id or "").strip()

    if not session_id:
        return None

    return Filter(
        must=[
            FieldCondition(
                key="session_id",
                match=MatchValue(
                    value=session_id
                )
            )
        ]
    )


# ============================================================
# SOURCE FILTER
# ============================================================

def build_source_filter(
    session_id: str,
    source_id: str
):
    session_id = str(session_id or "").strip()
    source_id = str(source_id or "").strip()

    if not session_id or not source_id:
        return None

    return Filter(
        must=[
            FieldCondition(
                key="session_id",
                match=MatchValue(
                    value=session_id
                )
            ),
            FieldCondition(
                key="source_id",
                match=MatchValue(
                    value=source_id
                )
            )
        ]
    )


# ============================================================
# STORE EMBEDDING
# ============================================================

def store_embedding(
    vector: list[float],
    text: str,
    metadata: dict
):
    if not vector:
        raise ValueError(
            "Embedding vector cannot be empty."
        )

    if not text or not text.strip():
        raise ValueError(
            "Text cannot be empty."
        )

    session_id = str(
        metadata.get(
            "session_id",
            ""
        )
    ).strip()

    source_id = str(
        metadata.get(
            "source_id",
            ""
        )
    ).strip()

    if not session_id:
        raise ValueError(
            "session_id is required when storing an embedding."
        )

    if not source_id:
        raise ValueError(
            "source_id is required when storing an embedding."
        )

    payload = {
        "text": text,
        **metadata,
        "session_id": session_id,
        "source_id": source_id
    }

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=payload
            )
        ],
        wait=True
    )


# ============================================================
# CHECK WHETHER SOURCE ALREADY EXISTS
# ============================================================

def source_exists(
    session_id: str,
    source_id: str
) -> bool:
    source_filter = build_source_filter(
        session_id=session_id,
        source_id=source_id
    )

    if source_filter is None:
        return False

    result = client.count(
        collection_name=COLLECTION_NAME,
        count_filter=source_filter,
        exact=True
    )

    return result.count > 0


# ============================================================
# DELETE ONE SOURCE
# ============================================================

def delete_source_vectors(
    session_id: str,
    source_id: str
):
    source_filter = build_source_filter(
        session_id=session_id,
        source_id=source_id
    )

    if source_filter is None:
        return

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=source_filter,
        wait=True
    )

    print(
        f"Deleted vectors for source "
        f"'{source_id}' in session '{session_id}'."
    )


# ============================================================
# DELETE ALL SESSION VECTORS
# ============================================================

def delete_session_vectors(
    session_id: str
):
    session_filter = build_session_filter(
        session_id
    )

    if session_filter is None:
        return

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=session_filter,
        wait=True
    )

    print(
        f"Deleted all vectors for session '{session_id}'."
    )


# ============================================================
# SEARCH EMBEDDINGS
# ============================================================

def search_embeddings(
    query_vector: list[float],
    limit: int = 5,
    session_id: str = ""
):
    if not query_vector:
        return []

    if limit <= 0:
        return []

    session_filter = build_session_filter(
        session_id
    )

    # Never perform an unfiltered search.
    # This is critical for session isolation.
    if session_filter is None:
        return []

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=session_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False
    )

    return results.points


# ============================================================
# CHECK WHETHER SESSION HAS VECTORS
# ============================================================

def session_has_vectors(
    session_id: str
) -> bool:
    session_filter = build_session_filter(
        session_id
    )

    if session_filter is None:
        return False

    result = client.count(
        collection_name=COLLECTION_NAME,
        count_filter=session_filter,
        exact=True
    )

    return result.count > 0