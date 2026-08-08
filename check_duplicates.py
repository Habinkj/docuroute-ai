"""
check_duplicates.py - confirm and quantify duplicate vectors in ChromaDB. FREE (no API calls at all - just reads the local store).

Hypothesis: the DB was populated more than once (old vectors not cleared before
re-ingest, or ingest.py ran twice), so every chunk exists 2+ times. That would
explain the 100% chunk1-vs-chunk2 overlap on every query.
"""

from collections import Counter
from langchain_community.vectorstores import Chroma

# No embedding function needed - we only read stored documents, we don't query.
vector_db = Chroma(persist_directory="./chroma_db")

data = vector_db.get()  # pulls all stored docs + metadata, no API call
docs = data["documents"]

print(f"Total vectors stored in ChromaDB: {len(docs)}")

counts = Counter(docs)
duplicated = {text: n for text, n in counts.items() if n > 1}

print(f"Unique chunk texts:               {len(counts)}")
print(f"Chunk texts stored more than once: {len(duplicated)}")

if duplicated:
    example_n = max(duplicated.values())
    print(f"\nCONFIRMED: duplicates present. Most-repeated chunk appears {example_n} times.")
    print("Root cause = the store was populated more than once.")
    print(f"You are storing ~{len(docs)} vectors when ~{len(counts)} would do.")
else:
    print("\nNo exact duplicates found - the redundancy is chunk OVERLAP, not double-ingest.")