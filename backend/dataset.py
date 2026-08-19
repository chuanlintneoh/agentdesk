from typing import Dict, Any
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction, SentenceTransformerEmbeddingFunction
import os
from helper.debug import debug_print

DATASET_PROFILES: Dict[str, Dict[str, Any]] = {
    "corporateAAPL": {
        "sql_path": "./data/corporateAAPL_sqlite.db",
        "chroma_path": "./data/corporateAAPL_chroma",
        "embedding_fn": DefaultEmbeddingFunction(),
    },
    "movies": {
        "sql_path": "./data/movies_sqlite.db",
        "chroma_path": "./data/movies_chroma",
        "embedding_fn": SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2", device="cpu"),
    },
    # locally chunked movies
    # "agentdesk": {
    #     "sql_path": "./data/agentdesk_sqlite.db",
    #     "chroma_path": "./data/agentdesk_chroma",
    #     "embedding_fn": DefaultEmbeddingFunction(),
    # }
}

ACTIVE_DATASET_NAME = os.getenv("ACTIVE_DATASET", "corporateAAPL")
current_profile: Dict[str, Any] = {}

def load_dataset_profile(dataset_name: str) -> None:
    global current_profile, ACTIVE_DATASET_NAME
    if dataset_name not in DATASET_PROFILES:
        debug_print(f"Failed to load profile for dataset '{dataset_name}'.")
        raise ValueError(f"Unknown dataset profile: '{dataset_name}'. Valid options: {list(DATASET_PROFILES.keys())}")
    
    ACTIVE_DATASET_NAME = dataset_name
    current_profile.clear()
    current_profile.update(DATASET_PROFILES[dataset_name])
    debug_print(f"Loaded dataset profile for '{dataset_name}': {current_profile}")

load_dataset_profile(ACTIVE_DATASET_NAME)