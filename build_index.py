import sqlite3
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

def fetch_chunks():
    """Fetch all chunk texts from the SQLite DB."""
    conn = sqlite3.connect("store/rag.db")
    cur = conn.cursor()
    cur.execute("SELECT text FROM chunks ORDER BY doc_id, chunk_id")
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]

def build_index(chunks):
    # 1. Load a pre-trained sentence embedding model
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # 2. Encode all chunks into dense vectors
    embeddings = model.encode(
        chunks,
        convert_to_numpy=True,        # return numpy array
        normalize_embeddings=True     # normalize so cosine similarity works
    )

    # embeddings.shape = (num_chunks, dim)
    dim = embeddings.shape[1]        # e.g., 384

    # 3. Create a FAISS index for cosine similarity
    index = faiss.IndexFlatIP(dim)   # IP = inner product (cosine sim with normalized vecs)

    # 4. Add vectors to the index
    index.add(embeddings.astype("float32"))

    # 5. Save the index and chunks
    faiss.write_index(index, "store/index.faiss")
    np.save("store/chunks.npy", np.array(chunks))

    print(f"FAISS index saved with {len(chunks)} chunks, dim={dim}.")

if __name__ == "__main__":
    chunks = fetch_chunks()
    print(f"Fetched {len(chunks)} chunks from DB.")
    build_index(chunks)
