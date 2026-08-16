import os
import sqlite3
import json
from typing import Optional
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import requests
from fastmcp import FastMCP
from helper.debug import debug_print

mcp = FastMCP("AgentDesk")

# DB_PATH = os.getenv("SQL_DB_PATH", "./data/agentdesk_sqlite.db")
# CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "./data/agentdesk_chroma")

# DB_PATH = os.getenv("SQL_DB_PATH", "corporateAAPL_sqlite.db")
# CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "./data/corporateAAPL_chroma")

DB_PATH = os.getenv("SQL_DB_PATH", "./data/movies_sqlite.db")
CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "./data/movies_chroma")

# Rule of Thumb: If tool waits for something external (network, disk, database), use async def. If only uses CPU and memory, use def.
@mcp.tool
def get_database_blueprint() -> str:
    """
    Returns the blueprint of the SQL database, including all available tables and their schemas.
    Call this tool first before writing any SQL queries to understand the schema.
    """
    debug_print("[MCP Execution] Retrieve database blueprint triggered.")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                return "Database is empty. No tables found."
            
            blueprint = []
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()
                table_schema = [f"Table: {table}"]
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    is_pk = " [PRIMARY KEY]" if col[5] == 1 else ""
                    table_schema.append(f"  - {col_name} ({col_type}){is_pk}")
                blueprint.append("\n".join(table_schema))
            return "\n\n".join(blueprint)
            
    except Exception as e:
        debug_print(f"Failed to retrieve database blueprint: {str(e)}")
        return f"Failed to retrieve database blueprint: {str(e)}"

@mcp.tool
def execute_sql_query(query: str) -> str:
    """
    Executes a read-only SQL SELECT query against the internal database.
    Use this tool to extract structured data.
    """
    debug_print(f"[MCP Execution] Execute SQL query triggered: {query}")
    try:
        # Strict security filter wrapper
        forbidden_cmds = ["drop", "delete", "update", "insert", "alter", "create"]
        if any(cmd in query.lower() for cmd in forbidden_cmds):
            return "Security Restriction: Write and structure alteration operations are strictly prohibited."

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            column_names = [desc[0] for desc in cursor.description]
            
            if not rows:
                return "Query executed successfully. Result set is empty."
                
            structured_data = [dict(zip(column_names, row)) for row in rows]
            return json.dumps(structured_data, indent=2)

    except Exception as e:
        debug_print(f"SQL Runtime failure: {str(e)}")
        return f"SQL Runtime failure: {str(e)}"

@mcp.tool
def list_vector_collections() -> str:
    """
    Lists all available semantic vector text collections stored in the RAG database.
    Use this first to discover available text vector spaces.
    """
    debug_print("[MCP Execution] Discovery triggered: Listing all vector collections...")
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        available_collections = client.list_collections()
        
        if not available_collections:
            return "Available vector collections: None (The vector database is empty)."
            
        names = [c.name for c in available_collections]
        return f"Available vector collections: {', '.join(names)}"
        
    except Exception as e:
        debug_print(f"Failed to list vector collections: {str(e)}")
        return f"Error listing vector collections: {str(e)}"

cpu_ef = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2",
    device="cpu"
)
@mcp.tool
def retrieve_text_context(
    collection_name: str,
    semantic_query: str,
    source_filter: Optional[str] = None
) -> str:
    """
    Performs a semantic similarity search inside a specific vector collection.

    Parameters:
    - collection_name: The exact name of the collection to search.
    - semantic_query: The natural language question or context theme to search for.
    - source_filter: Optional keyword/filename substring to restrict results to specific sources.
    """
    debug_print(f"[MCP Execution] Retrieve text context triggered: {semantic_query}")
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        try:
            collection = client.get_collection(
                name=collection_name.strip(),
                embedding_function=cpu_ef
            )
        except Exception:
            return f"Error: The vector collection '{collection_name}' does not exist. Use list_vector_collections to see valid options."

        query_kwargs = {"query_texts": [semantic_query], "n_results": 3}
        if source_filter and source_filter.strip():
            query_kwargs["where"] = {"source": {"$contains": source_filter.strip()}}
        
        # Querying the vector space database
        results = collection.query(**query_kwargs)
        
        extracted_text = []
        if results and 'documents' in results and results['documents'] and len(results['documents'][0]) > 0:
            for idx, text_block in enumerate(results['documents'][0]):
                # Dynamic metadata extraction for cleaner context mapping
                metadata = results['metadatas'][0][idx] if 'metadatas' in results and results['metadatas'] else {}
                source_file = metadata.get("source", "Unknown Asset")
                chunk_idx = metadata.get("chunk_idx", idx)

                extracted_text.append(
                    f"--- Context Block {idx+1} [Source: {source_file} | Chunk ID: {chunk_idx}] ---\n"
                    f"{text_block.strip()}\n"
                )
            return "\n".join(extracted_text)
        return f"Search execution succeeded, but no matching context chunks were found inside '{collection_name}'."
        
    except Exception as e:
        debug_print(f"Vector collection query runtime failure: {str(e)}")
        return f"Error executing vector query on '{collection_name}': {str(e)}"

# @mcp.tool
# def fetch_external_api_data(url: str, params_json: str = "") -> str:
#     """
#     Fetches real-time market data, travel schedules, or external API endpoints.
#     Use this to pull live contextual information from external web services.
    
#     Parameters:
#     - url: The absolute HTTP target URL address.
#     - params_json: Optional JSON string representing query parameters (defaults to empty string "").
#     """
#     debug_print(f"[MCP Execution] External API Fetch triggered: {url}")
#     try:
#         # Prevent accessing internal cluster infrastructure loops (SSRF protection)
#         if "localhost" in url or "127.0.0.1" in url or "backend" in url:
#             return "Security Restriction: Access to internal network routes is blocked."
            
#         params = json.loads(params_json) if params_json else None
#         response = requests.get(url, params=params, timeout=5)
        
#         if response.status_code != 200:
#             return f"External service responded with HTTP status code: {response.status_code}"
            
#         return response.text
#     except Exception as e:
#         debug_print(f"Network fetch error: {str(e)}")
#         return f"Network fetch error: {str(e)}"