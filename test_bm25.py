from search import bm25_search

print(bm25_search("safety*", top_k=3))
print(bm25_search("protective*", top_k=3))
print(bm25_search("equipment*", top_k=3))
