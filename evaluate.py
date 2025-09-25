# evaluate.py
import requests, csv, re, time
from pathlib import Path

URL = "http://127.0.0.1:9000/ask"  # <- set to your running port
K = 3

# 8 prompts (edit if you like)
DEFAULT_QUERIES = [
    "What is PPE?",
    "What is functional safety?",
    "What is EN ISO 13849-1?",
    "What does CELEX 2023/1230 regulate?",
    "What is machine guarding?",
    "What is a risk assessment?",
    "What is the role of safety relays?",
    "What does OSHA 3170 cover?",
]

def ask(q, mode):
    r = requests.post(URL, json={"q": q, "k": K, "mode": mode}, timeout=60)
    try:
        return r.json()
    except Exception:
        return {"error": r.text, "contexts": []}

def normalize(s):  # light cleanup for keyword check
    return re.sub(r"\s+", " ", (s or "")).lower()

def hit_at_k(query, contexts):
    """Very simple automatic check:
       returns 1 if any top-k context contains all words from the query (minus stop-words), else 0."""
    q = normalize(query)
    # crude keywords: remove tiny words
    qwords = [w for w in re.findall(r"[a-z0-9]+", q) if len(w) > 2]
    if not qwords:
        return 0
    for c in contexts:
        txt = normalize(c.get("text", ""))
        if all(w in txt for w in qwords):
            return 1
    return 0

def main():
    # load queries.txt if present, else use defaults
    if Path("questions.txt").exists():
        queries = [line.strip() for line in Path("questions.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        queries = DEFAULT_QUERIES

    rows = []
    summary = {"vector_hits": 0, "hybrid_hits": 0, "n": len(queries)}

    # CSV
    with open("evaluation.csv", "w", newline="", encoding="utf-8") as fcsv, \
         open("evaluation.md", "w", encoding="utf-8") as fmd:

        w = csv.writer(fcsv)
        w.writerow(["Query", "Mode", "Hit@{} (1/0)".format(K), "Top Context (truncated)"])

        fmd.write("| Query | Mode | Hit@{} | Top Context |\n".format(K))
        fmd.write("|-------|------|-------:|-------------|\n")

        for q in queries:
            for mode in ["vector", "hybrid"]:
                res = ask(q, mode)
                ctxs = res.get("contexts", []) or []
                top_preview = (ctxs[0]["text"][:140] + "…") if ctxs else ""
                hit = hit_at_k(q, ctxs)
                if mode == "vector": summary["vector_hits"] += hit
                else:                summary["hybrid_hits"] += hit

                w.writerow([q, mode, hit, top_preview])
                fmd.write(f"| {q} | {mode} | {hit} | {top_preview.replace('|','/')} |\n")
                print(f"✅ {q} [{mode}]  hit@{K}={hit}")
                time.sleep(0.05)

        # footer summary
        vec_rate = summary["vector_hits"] / summary["n"]
        hyb_rate = summary["hybrid_hits"] / summary["n"]
        imp = hyb_rate - vec_rate

        fmd.write("\n**Summary**\n\n")
        fmd.write(f"- Vector Hit@{K}: **{summary['vector_hits']}/{summary['n']}** ({vec_rate:.2%})\n")
        fmd.write(f"- Hybrid Hit@{K}: **{summary['hybrid_hits']}/{summary['n']}** ({hyb_rate:.2%})\n")
        fmd.write(f"- Δ Improvement: **{imp:+.2%}**\n")

    print("\nSaved evaluation.csv and evaluation.md ✅")
    print(f"Vector hits: {summary['vector_hits']}/{summary['n']}, Hybrid hits: {summary['hybrid_hits']}/{summary['n']}")
    print("Open evaluation.md and paste the summary/table into README.md.")

if __name__ == "__main__":
    main()
