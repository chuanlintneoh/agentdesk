import chromadb

# Initialize local ChromaDB client
client = chromadb.PersistentClient(path="./data/agentdesk_chroma")
collection = client.get_collection("movie_screenplays")

# Retrieve all items (omitting limit fetches the entire dataset)
results = collection.get(include=["metadatas"])

# Extract and deduplicate movie names from metadata
unique_movies = set()
for meta in results.get("metadatas", []):
    if meta:
        # Check common metadata keys for the file or movie name
        source = meta.get("source") or meta.get("title") or meta.get("movie")
        if source:
            unique_movies.add(source)

print(f"Total Chunks Indexed: {len(results['ids'])}\n")
print("All Unique Movies in Vector DB:")
for movie in sorted(unique_movies):
    print(f"- {movie}")