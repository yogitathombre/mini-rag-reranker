from search import HybridSearcher

hs = HybridSearcher()
for r in hs.topk("What is PPE?", k=3):
    print(f"Score={r['score']:.4f}")
    print(r["text"][:400], "\n---")
