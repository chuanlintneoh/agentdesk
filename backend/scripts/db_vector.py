# Download official annual disclosure (10-K report) directly from the SEC EDGAR system and save into local txt file for persistence
from sec_edgar_downloader import Downloader
import os
import glob
import re
from dotenv import load_dotenv
import chromadb

def download_company_10k(ticker: str = "AAPL", email_address: str = None):
    ticker_clean = ticker.upper().strip()

    print(f"Downloading {ticker_clean} latest 10-K filing...")
    os.makedirs(".tmp/", exist_ok=True)
    # Initialize the downloader
    dl = Downloader("AgentDesk", email_address, ".tmp")
    # Download the latest 10-K
    dl.get("10-K", ticker_clean, limit=1)
    # Locate the downloaded file
    search_pattern = f".tmp/sec-edgar-filings/{ticker_clean}/10-K/*/*.txt"
    download_path = glob.glob(search_pattern)

    if download_path:
        raw_file = download_path[0]
        print(f"Success! Raw 10-K saved to: {raw_file}")
        
        # Create a simplified text copy to make it easier to load into Vector DB
        with open(raw_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        # Clean up basic HTML tags
        clean_text = re.sub('<[^<]+?>', '', content)
        
        output_file = f".tmp/{ticker_clean.lower()}_10k_latest.txt"
        with open(output_file, "w", encoding="utf-8") as out:
            out.write(clean_text[:500000]) # Grabbing the first 500k characters for local practice limit
            
        print(f"Simplified text version generated: '{output_file}'")
    else:
        print("Failed to locate downloaded file.")
    
    return ticker_clean

def setup(ticker_clean: str, db: str = "./data/chroma_db"):
    source_file = f"./.tmp/{ticker_clean}_10k_latest.txt"
    if not os.path.exists(source_file):
        raise FileNotFoundError(f"Missing raw file: '{source_file}'")
    db_clean = db.lower().strip()

    print(f"1. Reading raw document '{source_file}'...")
    with open(source_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            # Move forward by chunk_size minus the overlap to keep context continuous
            start += (chunk_size - chunk_overlap)
        return chunks

    print("2. Chunking text...")
    text_chunks = chunk_text(raw_text, chunk_size=1000, chunk_overlap=200)
    print(f"Generated {len(text_chunks)} distinct chunks.")

    print(f"3. Initializing Chroma Persistent Client inside {db_clean}...")
    chroma_client = chromadb.PersistentClient(path=db_clean)
    collection_name = f"{ticker_clean.lower().strip()}_10k"
    collection = chroma_client.get_or_create_collection(name=collection_name)

    print(f"4. Vectorizing and storing chunks into collection {collection_name}...")
    ids = [f"chunk_{i}" for i in range(len(text_chunks))]
    metadatas = [{"source": source_file, "index": i} for i in range(len(text_chunks))]
    collection.upsert(
        ids=ids,
        documents=text_chunks,
        metadatas=metadatas
    )

    print("RAG vector database successfully created!")

def setup_vector(ticker: str, db: str = "./data/chroma_db"):
    load_dotenv()
    env_email = os.getenv("EMAIL_ADDRESS")
    ticker_clean = download_company_10k(ticker=ticker, email_address=env_email)
    setup(ticker_clean, db)