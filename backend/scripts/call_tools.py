from tools import retrieve_text_context, list_vector_collections

print("=== 1. Vector Collections ===")
collections = list_vector_collections()
print(collections)

print("\n=== 2. Vector Search Query ===")
res = retrieve_text_context(
    collection_name="movie_screenplays",
    semantic_query="sing scene in Rush Hour movie"
)
print(res)