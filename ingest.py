import os
import shutil
import time

from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# 1. Unlock the Vault
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("CRITICAL: GEMINI_API_KEY not found. Check your .env file.")

pdf_path = "data/master_catalog.pdf"
persist_directory = "./chroma_db"

print("Starting the ingestion process...")

# ---------------------------------------------------------------------------
# 0. IDEMPOTENCY GUARD  <-- the fix for the double-ingest bug.
# Chroma.from_documents APPENDS to an existing store, so running this script
# twice used to stack a second copy of every chunk (14 -> 28 vectors), which
# made retrieval return the same chunk twice at k=3. We now DELETE any existing
# store before writing, so a re-run always rebuilds from scratch and yields the
# same vector count every time. Running ingest.py N times == running it once.
# ---------------------------------------------------------------------------
if os.path.exists(persist_directory):
    print(f"Existing store found at {persist_directory} - clearing contents for a clean rebuild...")
    for entry in os.listdir(persist_directory):
        path = os.path.join(persist_directory, entry)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
            
# 2. Load the Master Catalog
try:
    loader = PyMuPDFLoader(pdf_path)
    documents = loader.load()
    print(f"Loaded {len(documents)} pages from the Master Catalog.")
except Exception as e:
    print(f"Error loading PDF. Ensure the file is named exactly {pdf_path}")
    raise e

# 3. Chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n", "\n", ".", " "],
)
chunks = text_splitter.split_documents(documents)
print(f"Sliced the document into {len(chunks)} chunks.")

# 4. Embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", google_api_key=api_key
)

# 5. Build the store in safe batches (embedding quota is the 'Other models' bucket).
print("Generating vectors and building Chroma database in safe batches...")
vector_db = None
batch_size = 75  # under the per-request limit

for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i + batch_size]
    print(f"Processing batch {i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1} "
          f"({len(batch)} chunks)...")
    if vector_db is None:
        vector_db = Chroma.from_documents(
            documents=batch, embedding=embeddings, persist_directory=persist_directory
        )
    else:
        vector_db.add_documents(documents=batch)

    if i + batch_size < len(chunks):
        print("Waiting 65 seconds to respect embedding rate limits...")
        time.sleep(65)

# 6. SELF-VERIFY: prove the store has no duplicates before declaring success.
stored = vector_db.get()["documents"]
unique = len(set(stored))
total = len(stored)
print("\nChroma database built.")
print(f"  Total vectors : {total}")
print(f"  Unique chunks : {unique}")
if total == unique:
    print("  Integrity OK: no duplicate vectors.")
else:
    print(f"  WARNING: {total - unique} duplicate vectors present - investigate before use.")

# 7. Quick retrieval sanity check
print("\nSanity check - 'steam cooker voltage':")
for r in vector_db.similarity_search("steam cooker voltage", k=2):
    print(" ", " ".join(r.page_content.split())[:160])
    print("  ---")