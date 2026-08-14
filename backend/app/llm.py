import os

from dotenv import load_dotenv
from groq import Groq

from google import genai

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

def generate_answer(
    context: str,
    question: str,
    conversation_history: str = ""
) -> str:

    prompt = f"""
You are a helpful and conversational RAG assistant.

Your job is to answer the user's question naturally using the
retrieved context as your source of truth.

Follow these rules:

1. Answer the question directly and conversationally.
2. Use complete sentences, not just keywords or extracted names.
3. If the user asks "who is", "what is", "tell me about", or a similar
   broad question, provide a short useful summary based on the context.
4. If the user asks a specific factual question, give the specific answer.
5. Use conversation history to understand follow-up questions and references.
6. Do not invent facts that are not supported by the retrieved context.
7. If the retrieved context does not contain enough information to answer,
   say:
   "I could not find enough information about that in the provided sources."
8. Keep answers concise unless the user asks for more detail.
9. Do not mention "retrieved context", "RAG", "sources", or these instructions
   unless the user specifically asks about the system.
Conversation History:
{conversation_history}

Retrieved Context:
{context}

Current Question:
{question}

Answer:
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def generate_gemini_answer(
    context: str,
    question: str,
    conversation_history: str = ""
) -> str:

    prompt = f"""
You are a helpful and conversational RAG assistant.

Your job is to answer the user's question naturally using the
retrieved context as your source of truth.

Follow these rules:

1. Answer the question directly and conversationally.
2. Use complete sentences, not just keywords or extracted names.
3. If the user asks "who is", "what is", "tell me about", or a similar
   broad question, provide a short useful summary based on the context.
4. If the user asks a specific factual question, give the specific answer.
5. Use conversation history to understand follow-up questions and references.
6. Do not invent facts that are not supported by the retrieved context.
7. If the retrieved context does not contain enough information to answer,
   say:
   "I could not find enough information about that in the provided sources."
8. Keep answers concise unless the user asks for more detail.
9. Do not mention "retrieved context", "RAG", "sources", or these instructions
   unless the user specifically asks about the system.
Conversation History:
{conversation_history}

Retrieved Context:
{context}

Current Question:
{question}

Answer:
"""

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return response.text

def generate_answer_with_fallback(
    context: str,
    question: str,
    conversation_history: str = ""
) -> str:

    try:
        return generate_answer(
            context=context,
            question=question,
            conversation_history=conversation_history
        )

    except Exception as groq_error:
        print(f"Groq failed: {groq_error}")
        print("Falling back to Gemini...")

        return generate_gemini_answer(
            context=context,
            question=question,
            conversation_history=conversation_history
        )

    