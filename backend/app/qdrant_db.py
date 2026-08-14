import os
from qdrant_client.models import Distance, VectorParams

from dotenv import load_dotenv
from qdrant_client import QdrantClient

from qdrant_client.models import PointStruct
import uuid
 
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)



COLLECTION_NAME = "voice_rag_documents"


def create_collection():
    collections = client.get_collections()

    existing_collections = [
        collection.name for collection in collections.collections
    ]

    if COLLECTION_NAME not in existing_collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=3072,
                distance=Distance.COSINE
            )
        )

        print(f"Collection '{COLLECTION_NAME}' created.")
    else:
        print(f"Collection '{COLLECTION_NAME}' already exists.")


# funtion used to store the vectors

def store_embedding(
    vector: list[float],
    text: str,
    metadata: dict
):
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": text,
                    **metadata
                }
            )
        ]
    )


# Add a search function ,Qdrant retrieval
def search_embeddings(
    query_vector: list[float],
    limit: int = 5
):
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True,
        with_vectors=False
    )

    return results.points