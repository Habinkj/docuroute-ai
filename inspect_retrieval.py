"""
inspect_retrieval.py - Pillar 3 diagnosis, (almost) FREE.

Shows EXACTLY what your retriever pulls from ChromaDB for a query, so you can SEE
redundancy / poisoning / irrelevance with your own eyes - WITHOUT calling the
expensive generation LLM. Retrieval uses one embedding call per query, which hits
the 'Other models' quota bucket (1K/day), NOT your scarce 20 RPD text bucket.

What it reveals:
  - Are the top-k chunks DISTINCT, or overlapping copies of the same passage?
  - How much do adjacent chunks overlap (a proxy for wasted retrieval slots)?
  - Does a query about machine A retrieve chunks about machine B (poisoning)?

Run: python inspect_retrieval.py
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", google_api_key=api_key
)
vector_db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

# Queries that should each pull DISTINCT facts. If retrieval returns duplicates,
# the redundancy bug is real and visible.
TEST_QUERIES = [
    "What is the voltage of the Industrial Steam Cooker?",
    "How much can the spiral freezer hold?",
    "Which machine is used for fish?",
]

K = 3  # match agent.py's retriever setting


def overlap_ratio(a, b):
    """Rough word-overlap between two chunks (0..1). High = redundant."""
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def inspect(query):
    print("=" * 70)
    print(f"QUERY: {query}")
    print("=" * 70)
    docs = vector_db.similarity_search(query, k=K)
    print(f"Retrieved {len(docs)} chunks (k={K}):\n")

    texts = [d.page_content for d in docs]
    for i, t in enumerate(texts, 1):
        preview = " ".join(t.split())[:180]
        print(f"  [chunk {i}] {preview}...")
        print()

    # Pairwise redundancy check
    print("  Redundancy between chunks (word overlap):")
    redundant = False
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            r = overlap_ratio(texts[i], texts[j])
            flag = "  <-- HIGH, likely redundant" if r > 0.5 else ""
            if r > 0.5:
                redundant = True
            print(f"    chunk {i+1} vs chunk {j+1}: {r:.0%}{flag}")
    if redundant:
        print("\n  FINDING: retrieval is spending slots on overlapping content.")
    else:
        print("\n  Chunks look distinct for this query.")
    print()


if __name__ == "__main__":
    print("Pillar 3 - retrieval inspection (no generation LLM call)\n")
    for q in TEST_QUERIES:
        inspect(q)
    print("Done. If HIGH overlaps appear, the chunk_overlap/k settings are the lever.")