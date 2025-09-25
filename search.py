# search.py
import sqlite3, re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# -----------------------
# BM25 Search
# -----------------------
import sqlite3, re



import sqlite3, re

def bm25_search(query, top_k=10):
    # normalize spaces + lowercase
    q = re.sub(r"\s+", " ", query.strip().lower())
    if not q:
        return []

    # tokenize: remove all non-alphanumeric chars
    raw_tokens = [t for t in q.split(" ") if t]
    tokens = []
    for t in raw_tokens:
        t_clean = re.sub(r"[^a-z0-9]", "", t)  # only letters & digits
        if t_clean:
            tokens.append(t_clean)

    if not tokens:
        return []

    # build FTS5 query with OR + wildcard
    qexpr = " OR ".join(f"{t}*" for t in tokens).replace("'", "''")

    con = sqlite3.connect("store/rag.db")
    cur = con.cursor()
    sql = f"""
        SELECT rowid, text, bm25(chunks_fts) AS score
        FROM chunks_fts
        WHERE text MATCH '{qexpr}'
        ORDER BY score
        LIMIT {top_k}
    """
    rows = cur.execute(sql).fetchall()
    con.close()

    return [{"rowid": int(r[0]), "text": r[1], "bm25": -float(r[2])} for r in rows]

# -----------------------
# Vector Searcher
# -----------------------
class VectorSearcher:
    def __init__(self):
        self.index = faiss.read_index("store/index.faiss")
        self.chunks = np.load("store/chunks.npy", allow_pickle=True)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def topk(self, query, k=5):
        q_emb = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        D, I = self.index.search(q_emb.astype("float32"), k)

        results = []
        for idx, score in zip(I[0], D[0]):
            results.append({"score": float(score), "text": self.chunks[idx]})
        return results


# -----------------------
# Hybrid Searcher
# -----------------------
class HybridSearcher(VectorSearcher):
    def __init__(self):
        super().__init__()   # load FAISS + model

    def topk(self, query, k=5, alpha=0.6):
        vec_results = super().topk(query, k=10)
        bm_results  = bm25_search(query, top_k=10)

        if not vec_results:
            return []

        bm_map = {r["text"]: r["bm25"] for r in bm_results}

        def norm(scores):
            if not scores:
                return {}
            lo, hi = min(scores.values()), max(scores.values())
            if hi == lo:
                return {k: 0.0 for k in scores}
            return {k: (v - lo) / (hi - lo) for k, v in scores.items()}

        v_scores = {r["text"]: r["score"] for r in vec_results}
        b_scores = bm_map

        v_norm = norm(v_scores)
        b_norm = norm(b_scores)

        merged = []
        for r in vec_results:
            txt = r["text"]
            v   = v_norm.get(txt, 0.0)
            b   = b_norm.get(txt, 0.0)
            final = alpha * v + (1 - alpha) * b
            merged.append({
                "text": txt,
                "score_vec": r["score"],
                "score_bm25": bm_map.get(txt, 0.0),
                "score": final
            })

        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:k]
