from fastapi import FastAPI
from pydantic import BaseModel
from search import VectorSearcher, HybridSearcher
from openai import OpenAI
from fastapi import FastAPI
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()  # load values from .env into environment

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



app = FastAPI()

vs = VectorSearcher()
hs = HybridSearcher()


class Query(BaseModel):
    q: str
    k: int = 3
    mode: str = "hybrid"

def generate_answer(question, contexts):
    context_text = "\n".join(c["text"] for c in contexts)
    # Return fake answer so pipeline works without quota
    return f"[MOCK ANSWER] Q: {question}\nBased on {len(contexts)} retrieved chunks."


@app.post("/ask")
def ask(query: Query):   # 👈 use Pydantic model
    try:
        if query.mode == "hybrid":
            results = hs.topk(query.q, k=query.k)
        else:
            results = vs.topk(query.q, k=query.k)

        answer = generate_answer(query.q, results)

        return {
            "answer": answer,
            "contexts": results,
            "reranker_used": query.mode
        }

    except Exception as e:
        # Debug error response
        return {"error": str(e)}