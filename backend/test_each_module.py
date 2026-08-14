# from app.extractors import extract_pdf_text,extract_txt_text, extract_pptx_text

# pdf_path = "uploads/Subramanian_T.pdf"

# text = extract_pdf_text(pdf_path)

# print(text[:100])



#-----------------------------------
# txt_path = "uploads/test.txt"

# text = extract_txt_text(txt_path)

# print(text)

#---------------------------------
# pptx_path = "uploads/RA2432241040050.pptx"

# text = extract_pptx_text(pptx_path)

# print(text[:2000])

#---------------------------------------------
# # test url scraper ...
# from app.scraper import scrape_url


# url = "https://huggingface.co/"

# text = scrape_url(url)

# print(text[:2000])

#------------------------------------------------
# test chunker.py
# from app.chunker import chunk_text


# text = """
# This is a test document for our Voice-Based Multi-Source RAG Assistant.
# We will eventually process PDF, TXT, PPTX and website content.
# The extracted content will be divided into smaller chunks before embeddings
# are generated and stored in Qdrant Cloud.
# """


# chunks = chunk_text(text)

# print("Number of chunks:", len(chunks))

# for i, chunk in enumerate(chunks, start=1):
#     print(f"\n--- Chunk {i} ---")
#     print("Characters:", len(chunk))
#     print(chunk[:100], "...")
#---------------------------------------------------
#test embeddings.py

# from app.embeddings import generate_embedding


# text = "This is a test document for our RAG system."

# embedding = generate_embedding(text)

# print("Embedding type:", type(embedding))
# print("Embedding dimensions:", len(embedding))
# print("First 5 values:", embedding[:5])

#----------------------------------------------------
# test the Qdrant Cloud connection
# from app.qdrant_db import client


# collections = client.get_collections()

# print("Connected to Qdrant Cloud successfully.")
# print("Collections:", collections)

# from app.qdrant_db import create_collection, client, COLLECTION_NAME


# create_collection()

# collection = client.get_collection(COLLECTION_NAME)

# print("Collection:", collection)

#---------------------------------------------
#test storing one real embedding in Qdrant.
# from app.embeddings import generate_embedding
# from app.qdrant_db import store_embedding, client, COLLECTION_NAME


# text = "Refunds are allowed within 7 days of purchase."

# vector = generate_embedding(text)

# metadata = {
#     "source_type": "pdf",
#     "source_name": "refund-policy.pdf",
#     "source_url": None
# }

# store_embedding(
#     point_id=1,
#     vector=vector,
#     text=text,
#     metadata=metadata
# )

# collection = client.get_collection(COLLECTION_NAME)

# print("Points stored:", collection.points_count)


#----------------------------------------
#testing processor.py
#extraction part
# from app.processor import extract_file_text


# source = {
#     "file_path": "uploads/Subramanian_T.pdf",
#     "source_name": "Subramanian_T.pdf",
#     "source_type": "pdf"
# }

# text = extract_file_text(source)

# print("Extracted characters:", len(text))
# print(text[:500])

#--------
#chunking part
# from app.processor import process_file


# source = {
#     "file_path": "uploads/Subramanian_T.pdf",
#     "source_name": "Subramanian_T.pdf",
#     "source_type": "pdf"
# }

# chunks = process_file(source)

# print("Number of chunks:", len(chunks))

# for i, chunk in enumerate(chunks[:3], start=1):
#     print(f"\n--- Chunk {i} ---")
#     print("Characters:", len(chunk))
#     print(chunk[:300])

#-----------------
# embedding part
# from app.processor import process_file, embed_chunks


# source = {
#     "file_path": "uploads/Subramanian_T.pdf",
#     "source_name": "Subramanian_T.pdf",
#     "source_type": "pdf"
# }

# chunks = process_file(source)

# embeddings = embed_chunks(chunks)

# print("Number of chunks:", len(chunks))
# print("Number of embeddings:", len(embeddings))

# for i, vector in enumerate(embeddings, start=1):
#     print(f"Chunk {i} embedding dimensions:", len(vector))

#-------------
# testing Store the processed chunks, embedding and metadata in Qdrant
# from app.processor import process_file, embed_chunks, store_chunks
# from app.qdrant_db import client, COLLECTION_NAME


# source = {
#     "file_path": "uploads/Subramanian_T.pdf",
#     "source_name": "Subramanian_T.pdf",
#     "source_type": "pdf"
# }

# chunks = process_file(source)

# embeddings = embed_chunks(chunks)

# store_chunks(
#     chunks=chunks,
#     embeddings=embeddings,
#     source=source,
#     start_id=100
# )

# collection = client.get_collection(COLLECTION_NAME)

# print("Points stored:", collection.points_count)


#--------------------
#testing after apply uuid
# from app.processor import process_file, embed_chunks, store_chunks
# from app.qdrant_db import client, COLLECTION_NAME


# source = {
#     "file_path": "uploads/Subramanian_T.pdf",
#     "source_name": "Subramanian_T.pdf",
#     "source_type": "pdf"
# }

# chunks = process_file(source)
# embeddings = embed_chunks(chunks)

# store_chunks(
#     chunks=chunks,
#     embeddings=embeddings,
#     source=source
# )

# collection = client.get_collection(COLLECTION_NAME)

# print("Points stored:", collection.points_count)

#-------------------
#let's make sure Qdrant actually contains the metadata we expect.
#Verify the stored metadata

# from app.qdrant_db import client, COLLECTION_NAME


# result = client.scroll(
#     collection_name=COLLECTION_NAME,
#     limit=3,
#     with_payload=True,
#     with_vectors=False
# )

# points = result[0]

# for point in points:
#     print("\nPoint ID:", point.id)
#     print("Payload:", point.payload)

#----------------------
#Now test the complete single-document processing pipeline.
# from app.processor import process_source


# source = {
#     "file_path": "uploads/Subramanian_T.pdf",
#     "source_name": "Subramanian_T.pdf",
#     "source_type": "pdf"
# }

# chunks_processed = process_source(source)

# print("Chunks processed:", chunks_processed)

#--------------------------------
# Now test the URL processing pipeline independently.

# from app.scraper import scrape_url
# from app.processor import process_url


# url = "https://www.knotopian.com/"

# text = scrape_url(url)

# source = {
#     "url": url,
#     "text": text,
#     "source_type": "url"
# }

# chunks_processed = process_url(source)

# print("URL:", url)
# print("Chunks processed:", chunks_processed)

#---------------------
#Test process_all_sources()
# from app.processor import process_all_sources


# uploaded_sources_test = [
#     {
#         "file_path": "uploads/Subramanian_T.pdf",
#         "source_name": "Subramanian_T.pdf",
#         "source_type": "pdf"
#     }
# ]

# url_sources_test = [
#     {
#         "url": "https://www.linkedin.com/",
#         "text": "This is a test webpage for our RAG system.",
#         "source_type": "url"
#     }
# ]

# result = process_all_sources(
#     uploaded_sources=uploaded_sources_test,
#     url_sources=url_sources_test
# )

# print("Processing result:")
# print(result)


#---------------------------------------------
# test Qdrant retrieval before connecting it to /ask.

# from app.embeddings import generate_embedding
# from app.qdrant_db import search_embeddings


# query = "What programming languages does Subramanian know?"

# query_vector = generate_embedding(query)

# results = search_embeddings(
#     query_vector=query_vector,
#     limit=3
# )

# print("Number of results:", len(results))

# for i, point in enumerate(results, start=1):
#     print(f"\n--- Result {i} ---")
#     print("Score:", point.score)
#     print("Source:", point.payload.get("source_name"))
#     print("Text:", point.payload.get("text")[:300])

#-------------------
#let's test build_context().

# from app.embeddings import generate_embedding
# from app.qdrant_db import search_embeddings
# from app.processor import build_context


# query = "What programming languages does Subramanian know?"

# query_vector = generate_embedding(query)

# results = search_embeddings(
#     query_vector=query_vector,
#     limit=3
# )

# context = build_context(results)

# print("Context created successfully.")
# print("\n--- Context ---")
# print(context[:1500])

#------------------
#let's test Groq independently before connecting it to Qdrant.
# from app.llm import generate_answer


# context = """
# Subramanian knows Python, Java, and SQL.
# He has experience with Flask, Streamlit, LangChain, Ollama, FAISS, and RAG.
# """

# question = "What programming languages does Subramanian know?"

# answer = generate_answer(
#     context=context,
#     question=question
# )

# print("Answer:")
# print(answer)


#--------------------------
#test the complete RAG engine before connecting it to FastAPI.

# from app.processor import answer_question


# question = "What programming languages does Subramanian know?"

# result = answer_question(question)

# print("Answer:")
# print(result["answer"])

# print("\nSources:")
# for source in result["sources"]:
#     print(source)

#----------
# test gemini fallback llm
# from app.llm import generate_gemini_answer


# context = """
# Subramanian knows Python, Java, and SQL.
# """

# question = "What programming languages does Subramanian know?"

# answer = generate_gemini_answer(
#     context=context,
#     question=question
# )

# print("Gemini fallback answer:")
# print(answer)

#-----------------------------
#Now test the fallback wrapper.
# from app.llm import generate_answer_with_fallback


# context = """
# Subramanian knows Python, Java, and SQL.
# """

# question = "What programming languages does Subramanian know?"

# answer = generate_answer_with_fallback(
#     context=context,
#     question=question
# )

# print("Answer with fallback:")
# print(answer)

#-------------------------------------------------------------
#let's test the complete RAG engine with the fallback integrated

# from app.processor import answer_question


# question = "What programming languages does Subramanian know?"

# result = answer_question(question)

# print("Answer:")
# print(result["answer"])

# print("\nSources:")
# for source in result["sources"]:
#     print(source)
    

#----------------
# let's make sure these modified LLM functions still work with an empty history.

# from app.llm import generate_answer_with_fallback

# context = """
# Subramanian knows Python, Java, and SQL.
# """

# question = "What programming languages does Subramanian know?"

# answer = generate_answer_with_fallback(
#     context=context,
#     question=question,
#     conversation_history=""
# )

# print("Answer:")
# print(answer)

import asyncio

from app.tts import generate_speech


async def main():

    text = (
        "Hello Subramanian. "
        "This is a test of the text to speech system."
    )


    output_file = "test_output.mp3"


    await generate_speech(
        text=text,
        output_file=output_file
    )


    print(
        f"Audio generated successfully: {output_file}"
    )


if __name__ == "__main__":

    asyncio.run(main())