from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FilterSelector
from dotenv import load_dotenv
import os

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)
COLLECTION_NAME  = "voice_rag_documents"
client.delete(
    collection_name=COLLECTION_NAME,
    points_selector=FilterSelector(
        filter=Filter()
    ),
    wait=True
)
print("All vectors deleted successfully.")