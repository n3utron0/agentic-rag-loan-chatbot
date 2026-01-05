from rag.rag_query import load_chroma
from rag.rag_query import embed_query, retrieve_chunks, generate_answer
from agent.llm_vertex import llm_generate

# Load DB once
collection = load_chroma()

def rag_tool(query: str):
    # 1. Embed
    query_embedding = embed_query(query)

    # 2. Retrieve chunks
    retrieved_chunks = retrieve_chunks(collection, query_embedding, k=4)

    # 3. Generate strict grounded answer
    answer = generate_answer(query, retrieved_chunks)
    con_answer = consolidate_answer(answer)
    # 4. Return structured dict
    return {
        "answer": con_answer,
        "sources": [
            {"pdf_name": c["pdf_name"], "page_num": c["page_num"]}
            for c in retrieved_chunks
        ]
    }

def consolidate_answer(answer: str) -> str:
    system_prompt = """
You are a banking communication assistant.

Your task is to rewrite the text below so it is clear, concise, and easy for the general public to understand.

Guidelines:
- Keep all key information, but remove unnecessary words or repetition.
- Do not add, assume, or change any information or tone.
- Use simple and professional language suited for a bank’s customers.
- If the text is already clear and concise, leave it unchanged.

Return only the improved answer text.
"""

    prompt = f"""
{system_prompt}

ANSWER:
{answer}
"""

    try:
        condensed = llm_generate(prompt).strip()
        # Safety fallback
        return condensed if condensed else answer
    except Exception:
        # Absolute safety net
        return answer