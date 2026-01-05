# rag/chunker.py
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
RAW_DATA_FILE = "E:/Users/omkar/Documents/Learning/Machine Learning/Projects/RAG/data/pdf_extraction/raw_data.json"
OUTPUT_CHUNKS_FILE = "E:/Users/omkar/Documents/Learning/Machine Learning/Projects/RAG/data/chunks/chunks.json"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200


# ------------------------------------------------------------
# Load raw extracted data
# ------------------------------------------------------------ 
def load_raw_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------
# Create text splitter
# ------------------------------------------------------------
def get_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )


# ------------------------------------------------------------
# Chunk logic
# ------------------------------------------------------------
def create_chunks(raw_data):
    splitter = get_splitter()
    chunks = []

    for pdf in raw_data:
        pdf_name = pdf["pdf_name"]

        for page in pdf["pages"]:
            page_num = page["page_num"]
            text = page.get("text", "") or ""
            tables = page.get("tables", []) or []

            # ------------------------------------------------
            # 1. CHUNK TEXT
            # ------------------------------------------------
            if text.strip():  # Only if non-empty
                text_chunks = splitter.split_text(text)

                for idx, chunk_text in enumerate(text_chunks):
                    chunks.append({
                        "id": f"{pdf_name}_page{page_num}_chunk{idx}",
                        "pdf_name": pdf_name,
                        "page_num": page_num,
                        "content": chunk_text
                    })

            # ------------------------------------------------
            # 2. CHUNK TABLES (each table = ONE chunk)
            # ------------------------------------------------
            for t_idx, table_text in enumerate(tables):
                chunks.append({
                    "id": f"{pdf_name}_page{page_num}_table{t_idx}",
                    "pdf_name": pdf_name,
                    "page_num": page_num,
                    "content": table_text
                })

    return chunks


# ------------------------------------------------------------
# Save chunks into JSON
# ------------------------------------------------------------
def save_chunks(chunks, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=4, ensure_ascii=False)
    print(f"Saved chunks to: {output_path}")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
if __name__ == "__main__":
    print("Loading raw_data.json ...")
    raw_data = load_raw_data(RAW_DATA_FILE)

    print("Creating chunks (this may take a moment)...")
    chunks = create_chunks(raw_data)

    print(f"Total chunks created: {len(chunks)}")

    save_chunks(chunks, OUTPUT_CHUNKS_FILE)
