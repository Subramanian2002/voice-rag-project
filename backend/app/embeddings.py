import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

EMBEDDING_DIMENSION = 3072


def generate_embedding(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty.")

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config={
            "output_dimensionality": EMBEDDING_DIMENSION
        }
    )

    return response.embeddings[0].values