import os
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

print("Starting the ingestion process...")

# 2. Load the Master Catalog
pdf_path = "data/master_catalog.pdf"
try:
    loader = PyMuPDFLoader(pdf_path)
    documents = loader.load()
    print(f"Loaded {len(documents)} pages from the Master Catalog.")
except Exception as e:
    print(f"Error loading PDF. Ensure the file is named exactly {pdf_path}")
    raise e

# 3. The Slicer (Chunking Strategy)
# We use overlapping chunks to ensure context isn't lost if a sentence gets cut in half.
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n", "\n", ".", " "]
)
chunks = text_splitter.split_documents(documents)
print(f"Sliced the document into {len(chunks)} mathematical chunks.")

# 4. The Embedding Engine
# This converts English words into high-dimensional numerical vectors.
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# 5. Build the Vector Database
# This creates a persistent local folder named 'chroma_db' to store the vectors.
persist_directory = "./chroma_db"
print("Generating vectors and building Chroma database. This may take a moment...")

import time

print("Generating vectors and building Chroma database in safe batches...")

# Initialize an empty Chroma database first
vector_db = None
batch_size = 75  # Stay safely under the 100 limit

# Loop through chunks in safe increments
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i + batch_size]
    print(f"Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1} ({len(batch)} chunks)...")
    
    if vector_db is None:
        vector_db = Chroma.from_documents(
            documents=batch,
            embedding=embeddings,
            persist_directory=persist_directory
        )
    else:
        vector_db.add_documents(documents=batch)
    
    # Sleep for a full 65 seconds to guarantee the Google quota resets
    if i + batch_size < len(chunks):
        print("Waiting 65 seconds for Google API quota to reset. Do not close terminal...")
        time.sleep(65)

print("Chroma database successfully built and verified!")