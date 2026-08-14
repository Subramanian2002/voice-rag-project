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


load_dotenv()


QDRANT_URL = os.getenv(
    "QDRANT_URL"
)

QDRANT_API_KEY = os.getenv(
    "QDRANT_API_KEY"
)


if not QDRANT_URL:

    raise ValueError(
        "QDRANT_URL is not configured."
    )


if not QDRANT_API_KEY:

    raise ValueError(
        "QDRANT_API_KEY is not configured."
    )


client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)


COLLECTION_NAME = (
    "voice_rag_documents"
)


VECTOR_SIZE = 3072


# ============================================================
# CREATE COLLECTION
# ============================================================

def create_collection():

    collections = client.get_collections()

    existing_collections = [

        collection.name

        for collection
        in collections.collections

    ]


    if COLLECTION_NAME not in existing_collections:

        client.create_collection(

            collection_name=
                COLLECTION_NAME,

            vectors_config=
                VectorParams(

                    size=VECTOR_SIZE,

                    distance=
                        Distance.COSINE
                )
        )

        print(
            f"Collection '{COLLECTION_NAME}' created."
        )

    else:

        print(
            f"Collection '{COLLECTION_NAME}' already exists."
        )


    # Make sure the session_id field can be
    # efficiently filtered.

    create_session_index()


# ============================================================
# CREATE SESSION PAYLOAD INDEX
# ============================================================

def create_session_index():

    try:

        client.create_payload_index(

            collection_name=
                COLLECTION_NAME,

            field_name=
                "session_id",

            field_schema=
                PayloadSchemaType.KEYWORD
        )

        print(
            "Session ID payload index created."
        )

    except Exception as e:

        error_message = str(e).lower()


        # Qdrant may report that the index already exists.
        # That is not an application error.

        if (
            "already exists"
            in error_message
            or
            "duplicate"
            in error_message
        ):

            print(
                "Session ID payload index already exists."
            )

        else:

            raise


# ============================================================
# BUILD SESSION FILTER
# ============================================================

def build_session_filter(
    session_id: str
):

    if not session_id:

        return None


    session_id = str(
        session_id
    ).strip()


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


    # Never allow a vector to be stored without
    # a session ID.

    if not session_id:

        raise ValueError(
            "session_id is required when "
            "storing an embedding."
        )


    payload = {

        "text":
            text,

        **metadata,

        "session_id":
            session_id
    }


    client.upsert(

        collection_name=
            COLLECTION_NAME,

        points=[

            PointStruct(

                id=str(
                    uuid.uuid4()
                ),

                vector=vector,

                payload=payload
            )
        ],

        wait=True
    )


# ============================================================
# DELETE ALL VECTORS FOR ONE SESSION
# ============================================================

def delete_session_vectors(
    session_id: str
):

    session_id = str(
        session_id
    ).strip()


    if not session_id:

        raise ValueError(
            "session_id is required when "
            "deleting session vectors."
        )


    session_filter = (
        build_session_filter(
            session_id
        )
    )


    if session_filter is None:

        return


    try:

        result = client.delete(

            collection_name=
                COLLECTION_NAME,

            points_selector=
                session_filter,

            wait=True
        )


        print(
            f"Deleted existing vectors "
            f"for session: {session_id}"
        )


        return result


    except Exception as e:

        print(
            f"Failed to delete vectors "
            f"for session {session_id}: {e}"
        )

        raise


# ============================================================
# SEARCH EMBEDDINGS
# ============================================================

def search_embeddings(
    query_vector: list[float],
    limit: int = 5,
    session_id: str = ""
):

    session_id = str(
        session_id
    ).strip()


    # CRITICAL SECURITY RULE:
    #
    # Never perform a global Qdrant search.
    #
    # If there is no valid session ID, return no results.
    #
    # This prevents old data from another/currently inactive
    # session from being returned.

    if not session_id:

        print(
            "Qdrant search blocked: "
            "missing session_id."
        )

        return []


    if not query_vector:

        return []


    if limit <= 0:

        return []


    session_filter = (
        build_session_filter(
            session_id
        )
    )


    if session_filter is None:

        return []


    results = client.query_points(

        collection_name=
            COLLECTION_NAME,

        query=query_vector,

        query_filter=
            session_filter,

        limit=limit,

        with_payload=True,

        with_vectors=False
    )


    return results.points


# ============================================================
# OPTIONAL: CHECK WHETHER SESSION HAS DATA
# ============================================================

def session_has_vectors(
    session_id: str
) -> bool:

    session_id = str(
        session_id
    ).strip()


    if not session_id:

        return False


    session_filter = (
        build_session_filter(
            session_id
        )
    )


    if session_filter is None:

        return False


    try:

        result = client.count(

            collection_name=
                COLLECTION_NAME,

            count_filter=
                session_filter,

            exact=True
        )


        return result.count > 0


    except Exception as e:

        print(
            f"Session vector check failed: {e}"
        )

        return False