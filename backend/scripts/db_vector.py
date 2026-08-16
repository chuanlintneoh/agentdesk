# Corporate: Download official annual disclosure (10-K report) directly from the SEC EDGAR system and save into local txt file for persistence
# Movie: Parse raw screenplay text files from Kaggle dataset, chunk dialogues, and persist into Chroma vector store
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sec_edgar_downloader import Downloader
import glob
import re
from dotenv import load_dotenv
import chromadb
from helper.debug import debug_print

def extract_sec_edgar(ticker: str = "AAPL", email_address: str = None) -> list[dict]:
    ticker_clean = ticker.upper().strip()

    debug_print(f"Downloading {ticker_clean} latest 10-K filing...")
    os.makedirs(".tmp/", exist_ok=True)
    # Initialize the downloader
    dl = Downloader("AgentDesk", email_address, ".tmp")
    # Download the latest 10-K
    dl.get("10-K", ticker_clean, limit=1)
    # Locate the downloaded file
    search_pattern = f".tmp/sec-edgar-filings/{ticker_clean}/10-K/*/*.txt"
    download_path = glob.glob(search_pattern)

    if not download_path:
        debug_print("Failed to locate downloaded SEC disclosure file.")
        return []

    raw_file = download_path[0]
    debug_print(f"Success! Raw 10-K saved to: {raw_file}")
    
    # Create a simplified text copy to make it easier to load into Vector DB
    with open(raw_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    # Clean up basic HTML tags
    clean_text = re.sub('<[^<]+?>', '', content)
    truncated_text = clean_text[:500000] # Grabbing the first 500k characters for local practice limit
    
    return [{
        "id": f"corp_{ticker_clean.lower()}_10k_latest",
        "text": truncated_text,
        "metadata": {
            "ticker": ticker_clean,
            "source": f"{ticker_clean.lower()}_10k_latest.txt",
            "type": "10-K"
        }
    }]

def extract_movie_dataset(dataset_path: str = ".tmp/movies/movie-scripts-corpus") -> list[dict]:
    # https://www.kaggle.com/datasets/gufukuro/movie-scripts-corpus
    raw_texts_dir = os.path.join(dataset_path, "screenplay_data", "data", "raw_texts", "raw_texts")
    if not os.path.exists(raw_texts_dir):
        raise FileNotFoundError(f"Missing dataset path: '{raw_texts_dir}'")
    
    debug_print(f"Extracting movie script text nodes from: {raw_texts_dir}...")

    unified_payloads = []
    for idx, file in enumerate(os.listdir(raw_texts_dir)):
        if idx >= 50:
            # NOTE: Limit for local testing purposes
            break
        if file.endswith(".txt"):
            file_path = os.path.join(raw_texts_dir, file)
            movie_id = file.split(".")[0]
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    script_content = f.read()
                unified_payloads.append({
                    "id": f"movie_script_{movie_id}",
                    "text": script_content,
                    "metadata": {
                        "movie_id": movie_id,
                        "source": file,
                        "type": "screenplay"
                    }
                })
            except Exception as e:
                debug_print(f"Skipping problematic script file {file}: {str(e)}")

    return unified_payloads

def save_to_chroma(
    payloads: list[dict],
    collection_name: str,
    db: str = "./data/agentdesk_chroma",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    batch_size: int = 500
):
    if not payloads:
        debug_print("Save operation aborted: Received empty payload array lists.")
        return
    
    debug_print(f"Initializing Chroma Persistent Client inside {db}...")
    chroma_client = chromadb.PersistentClient(path=db)
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    documents_to_upsert = []
    ids_to_upsert = []
    metadatas_to_upsert = []

    debug_print(f"Processing and chunking {len(payloads)} base data assets...")
    # Unpack document models matching standard layout contracts
    for item in payloads:
        base_id = item["id"]
        text_content = item["text"]
        base_metadata = item["metadata"]

        start = 0
        step = 0
        while start < len(text_content):
            end = start + chunk_size
            chunk = text_content[start:end]
            
            documents_to_upsert.append(chunk)
            ids_to_upsert.append(f"{base_id}_chunk_{step}")
            
            # Merge context indexing counters straight into base metadata dictionaries
            merged_meta = {**base_metadata, "chunk_idx": step}
            metadatas_to_upsert.append(merged_meta)
            
            start += (chunk_size - chunk_overlap)
            step += 1

    debug_print(f"Vectorizing and storing {len(documents_to_upsert)} total split chunks...")
    for i in range(0, len(documents_to_upsert), batch_size):
        collection.upsert(
            ids=ids_to_upsert[i:i + batch_size],
            documents=documents_to_upsert[i:i + batch_size],
            metadatas=metadatas_to_upsert[i:i + batch_size]
        )
    
    debug_print("RAG vector database successfully updated and synchronized!")

    # def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
    #     chunks = []
    #     start = 0
    #     while start < len(text):
    #         end = start + chunk_size
    #         chunks.append(text[start:end])
    #         # Move forward by chunk_size minus the overlap to keep context continuous
    #         start += (chunk_size - chunk_overlap)
    #     return chunks

    # debug_print("2. Chunking text...")
    # text_chunks = chunk_text(raw_text, chunk_size=1000, chunk_overlap=200)
    # debug_print(f"Generated {len(text_chunks)} distinct chunks.")

    # debug_print(f"4. Vectorizing and storing chunks into collection {collection_name}...")
    # ids = [f"chunk_{i}" for i in range(len(text_chunks))]
    # metadatas = [{"source": source_file, "index": i} for i in range(len(text_chunks))]
    # collection.upsert(
    #     ids=ids,
    #     documents=text_chunks,
    #     metadatas=metadatas
    # )

def setup_corporate_vectordb(ticker: str, db: str = "./data/agentdesk_chroma"):
    load_dotenv()
    env_email = os.getenv("EMAIL_ADDRESS")
    corporate_payloads = extract_sec_edgar(ticker=ticker, email_address=env_email)
    collection_name = f"{ticker.lower().strip()}_10k"
    save_to_chroma(payloads=corporate_payloads, collection_name=collection_name, db=db)

def setup_movie_vectordb(dataset_path: str = ".tmp/movies/movie-scripts-corpus", db: str = "./data/agentdesk_chroma"):
    movie_payloads = extract_movie_dataset(dataset_path=dataset_path)
    collection_name = "movie_screenplays"
    save_to_chroma(payloads=movie_payloads, collection_name=collection_name, db=db)