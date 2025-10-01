Mini RAG + Reranker (Industrial Safety PDFs)

A tiny QA service over ~20 public PDFs.
Pipeline: ingest → chunk → SQLite (docs+chunks+FTS) → FAISS embeddings → baseline vector search → hybrid reranker (BM25 + vectors) → answer generation (OpenAI or mock).

Features

Chunking (paragraph-ish, 300–900 chars)

SQLite: docs, chunks, chunks_fts (FTS5 for BM25)

Embeddings: all-MiniLM-L6-v2 + FAISS (cosine via inner product)

Baseline: top-k vector search

Reranker: hybrid (blend normalized vector score + BM25)

API: POST /ask { q, k, mode } → { answer | null, contexts[], reranker_used }

Evaluation: 8 queries × 2 modes (vector/hybrid) with Hit@k

Setup
# 1) Create & activate venv
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

Environment variable (safe)

Create a .env file in the project root:

OPENAI_API_KEY=sk-xxxx...your real key...


.env is gitignored so your key stays private.

Data → DB → Index (one-time ingest)

Place the assessment files:

data/
  industrial-safety-pdfs.zip
  sources.json


Run ingest:

python ingest.py


This will:

unzip to pdfs/

read sources.json

extract text, chunk, and write to store/rag.db

build FAISS & save store/index.faiss + store/chunks.npy

create & backfill chunks_fts for BM25

Run the API
uvicorn main:app --reload --port 9090

Endpoint

POST /ask
Body:

{
  "q": "What is PPE?",
  "k": 3,
  "mode": "hybrid"   // "vector" or "hybrid"
}

Example (curl)
# Vector baseline
curl -X POST "http://127.0.0.1:9090/ask" \
  -H "Content-Type: application/json" \
  -d '{"q":"What is PPE?","k":3,"mode":"vector"}'

# Hybrid reranker
curl -X POST "http://127.0.0.1:9090/ask" \
  -H "Content-Type: application/json" \
  -d '{"q":"What is PPE?","k":3,"mode":"hybrid"}'

Example (Python)
import requests, json
res = requests.post("http://127.0.0.1:9090/ask",
    json={"q":"What is PPE?","k":3,"mode":"hybrid"})
print(json.dumps(res.json(), indent=2))

Evaluation

File: questions.txt (8 lines), then:

python evaluate.py


Outputs:

evaluation.csv (raw)

evaluation.md (pretty table + summary)

Sample Results (Hit@3)
Question	Mode	hit@3
What is PPE?	vector	0
What is PPE?	hybrid	0
What is functional safety?	vector	1
What is functional safety?	hybrid	1
What is EN ISO 13849-1?	vector	0
What is EN ISO 13849-1?	hybrid	0
What does CELEX 2023/1230 regulate?	vector	0
What does CELEX 2023/1230 regulate?	hybrid	0
What is machine guarding?	vector	0
What is machine guarding?	hybrid	0
What is a risk assessment?	vector	0
What is a risk assessment?	hybrid	0
What is the role of safety relays?	vector	0
What is the role of safety relays?	hybrid	0
What does OSHA 3170 cover?	vector	0
What does OSHA 3170 cover?	hybrid	0

Vector Hit@3: 1/8 (12.5%)
Hybrid Hit@3: 1/8 (12.5%)
Δ Improvement: 0%

Note: hybrid often helps; results vary with corpus and query phrasing. Try k=5 and more targeted queries for deeper checks.

Project Structure
.
├── data/
│   ├── industrial-safety-pdfs.zip
│   └── sources.json
├── pdfs/                    # created by ingest
├── store/
│   ├── rag.db
│   ├── index.faiss
│   └── chunks.npy
├── ingest.py                # unzip → extract → chunk → SQLite → FAISS
├── search.py                # VectorSearcher + HybridSearcher (BM25+vector)
├── main.py                  # FastAPI /ask endpoint + answer generation
├── evaluate.py              # batch eval for 8 queries, CSV/MD outputs
├── questions.txt            # the 8 evaluation queries
├── test_api.py              # quick request example
├── requirements.txt
├── .env                     # OPENAI_API_KEY=...  (gitignored)
└── README.md

Requirements
fastapi
uvicorn
pypdf
sentence-transformers
faiss-cpu
scikit-learn
numpy
requests
python-dotenv

Notes & What We Learned

Chunks ~300–900 chars work well for MiniLM.

FTS5 BM25 + FAISS hybridization is simple and effective to implement.

A tiny, honest evaluation (Hit@k) makes the before/after comparison clear.

Keep citations via sources.json (title + URL), and map them in responses if desired.

---

## Submission Details
- Candidate: Yogita Thombre
- Application ID: PD02-924
- Assessment: Mini RAG + Reranker Sprint
- Submitted: September 2025
