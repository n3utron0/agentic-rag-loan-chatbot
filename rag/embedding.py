# rag/embedding.py
import os
import json
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
import vertexai
from vertexai.preview.language_models import TextEmbeddingModel

load_dotenv()

# ============================================================
# CONFIG
# ============================================================
CHUNKS_FILE = "data/chunks/chunks.json"
CHROMA_DB_DIR = "data/chroma_db"
COLLECTION_NAME = "rag_chunks"

# Gemini / Vertex embedding model
EMBEDDING_MODEL_NAME = "gemini-embedding-001"   # Gemini Embedding

# How many chunks to embed in a single API call
BATCH_SIZE = 32


# ============================================================
# Vertex AI Setup
# ============================================================
def init_vertex_ai():
    """
    Initialize Vertex AI using environment variables:
      GCP_PROJECT_ID  -> Your GCP project
      GCP_REGION      -> Region (e.g. 'asia-south1')
    Credentials are taken from GOOGLE_APPLICATION_CREDENTIALS.
    """
    project_id = os.getenv("GCP_PROJECT_ID")
    region = os.getenv("GCP_REGION")

    if not project_id:
        raise ValueError(
            "GCP_PROJECT_ID environment variable is not set. "
            "Set it to your GCP project ID."
        )

    if not region:
        raise ValueError(
            "GCP_REGION environment variable is not set. "
            "Set it to your Vertex AI region (e.g. 'asia-south1')."
        )

    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise ValueError(
            "GOOGLE_APPLICATION_CREDENTIALS is not set. "
            "Point it to your service account JSON file."
        )
    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"Credentials file not found at: {creds_path}"
        )

    # Initialize Vertex AI client
    vertexai.init(project=project_id, location=region)
    print(f"✓ Vertex AI initialized (project={project_id}, region={region})")


def get_embedding_model():
    """
    Load the Vertex AI embedding model.
    Called once and reused for all batches.
    """
    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)
    print(f"✓ Loaded embedding model: {EMBEDDING_MODEL_NAME}")
    return model


# ============================================================
# Data Loading
# ============================================================
def load_chunks(path):
    """
    Load chunks from JSON file.
    Expected format:
    [
      {
        "id": "pricing-grid_p1_text_0",
        "pdf_name": "...",
        "page_num": 1,
        "content": "....."
      },
      ...
    ]
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Chunks file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"✓ Loaded {len(chunks)} chunks from {path}")
    return chunks


# ============================================================
# Chroma Initialization
# ============================================================
def init_chroma():
    """
    Initialize ChromaDB persistent client and collection.
    Creates the collection if it does not exist.
    """
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)

    client = chromadb.PersistentClient(
        path=CHROMA_DB_DIR,
        settings=Settings(allow_reset=True)
    )

    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"✓ Using existing Chroma collection: {COLLECTION_NAME}")
    except Exception:
        collection = client.create_collection(name=COLLECTION_NAME)
        print(f"✓ Created new Chroma collection: {COLLECTION_NAME}")

    return collection


# ============================================================
# Embedding Helpers
# ============================================================
def embed_batch(model, texts):
    """
    Embed a batch of texts with Vertex AI.
    `texts` is a list of strings.
    Returns a list of embedding vectors (list[float]).
    """
    try:
        responses = model.get_embeddings(texts)
        # Each response has `.values` which is the embedding vector
        vectors = [resp.values for resp in responses]
        return vectors
    except Exception as e:
        print(f"✗ Error embedding batch ({len(texts)} items): {e}")
        raise


def store_embeddings(chunks, collection, model):
    """
    Embed all chunks in batches and store them in Chroma DB.

    Each chunk is stored with:
      - id        -> chunk["id"]
      - document  -> chunk["content"]
      - metadata  -> { pdf_name, page_num }
      - embedding -> vector from Vertex AI
    """
    total = len(chunks)
    print(f"\nEmbedding {total} chunks in batches of {BATCH_SIZE}...\n")

    batch_ids = []
    batch_texts = []
    batch_metadatas = []

    embedded_count = 0
    failed_count = 0

    for idx, chunk in enumerate(chunks, start=1):
        chunk_id = chunk["id"]
        text = chunk["content"]
        metadata = {
            "pdf_name": chunk.get("pdf_name", ""),
            "page_num": chunk.get("page_num", None),
        }

        batch_ids.append(chunk_id)
        batch_texts.append(text)
        batch_metadatas.append(metadata)

        # When batch is full OR we are at the last chunk -> embed + store
        if len(batch_texts) == BATCH_SIZE or idx == total:
            try:
                # Get embeddings for this batch
                vectors = embed_batch(model, batch_texts)

                # Store in Chroma
                collection.add(
                    ids=batch_ids,
                    documents=batch_texts,
                    embeddings=vectors,
                    metadatas=batch_metadatas,
                )

                embedded_count += len(batch_texts)
                print(f"  ✓ Embedded {embedded_count}/{total} chunks")

            except Exception as e:
                print(f"  ✗ Failed batch ending at index {idx}: {e}")
                failed_count += len(batch_texts)

            # Reset batch buffers
            batch_ids = []
            batch_texts = []
            batch_metadatas = []

    print("\n------------------------------------------------")
    print(f"✓ Finished embedding pipeline")
    print(f"  Successfully embedded: {embedded_count}")
    print(f"  Failed: {failed_count}")
    return embedded_count, failed_count


def verify_chroma(collection):
    """
    Simple verification that documents are actually stored.
    """
    count = collection.count()
    print(f"\n✓ Chroma collection now contains {count} documents.")
    return count


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("RAG EMBEDDING PIPELINE (Vertex AI + Chroma)")
    print("=" * 60)

    try:
        print("\n[1/5] Initializing Vertex AI...")
        init_vertex_ai()

        print("\n[2/5] Loading embedding model...")
        model = get_embedding_model()

        print("\n[3/5] Loading chunks from JSON...")
        chunks = load_chunks(CHUNKS_FILE)

        print("\n[4/5] Initializing Chroma DB...")
        collection = init_chroma()

        print("\n[5/5] Embedding chunks and storing in Chroma...")
        success, failed = store_embeddings(chunks, collection, model)

        verify_chroma(collection)

        print("\n" + "=" * 60)
        print("✓ EMBEDDING COMPLETE")
        print("=" * 60)
        print(f"Total chunks: {len(chunks)}")
        print(f"Successfully embedded: {success}")
        print(f"Failed: {failed}")
        print(f"Chroma DB path: {os.path.abspath(CHROMA_DB_DIR)}")

    except Exception as e:
        print("\n✗ Fatal error in embedding pipeline:")
        print(e)
        print("\nCheck:")
        print("  - GOOGLE_APPLICATION_CREDENTIALS points to valid JSON")
        print("  - GCP_PROJECT_ID and GCP_REGION are set")
        print("  - chunks file path is correct")
