import sqlite3
import chromadb
from fastmcp import FastMCP
from numpy.random import f

from helper.debug import debug_print

mcp = FastMCP("AgentDesk")

DB_PATH = "./data/agentdesk.db"
CHROMA_PATH = "./data/chroma_db"

@mcp.tool
def list_database_tables() -> str:
    """
    Returns a list of all available tables inside the SQL database.
    Call this tool first before writing any SQL queries to understand the schema.
    """
    debug_print("[MCP Execution] List database tables triggered.")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return f"Available database tables: {', '.join(tables)}"
    except Exception as e:
        debug_print(f"Failed to retrieve tables: {str(e)}")
        return f"Failed to retrieve tables: {str(e)}"

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

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        column_names = [desc[0] for desc in cursor.description]
        conn.close()
        
        if not rows:
            return "Query executed successfully. Result set is empty."
            
        import json
        structured_data = [dict(zip(column_names, row)) for row in rows]
        return json.dumps(structured_data, indent=2)

    except Exception as e:
        debug_print(f"SQL Runtime failure: {str(e)}")
        return f"SQL Runtime failure: {str(e)}"

@mcp.tool
def retrieve_text_context(semantic_query: str) -> str:
    """
    Performs a semantic vector RAG search across text chunks.
    Use this tool to answer qualitative questions.
    """
    debug_print(f"[MCP Execution] Retrieve text context triggered: {semantic_query}")
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_collection(name="aapl_10k")

        # Querying the vector space database
        results = collection.query(
            query_texts=[semantic_query],
            n_results=3
        )
        
        extracted_text = []
        if results and 'documents' in results and results['documents']:
            for idx, text_block in enumerate(results['documents'][0]):
                extracted_text.append(f"--- Document Context Piece {idx+1} ---\n{text_block.strip()}\n")
            return "\n".join(extracted_text)
        return "No corresponding textual context chunks could be retrieved."
        
    except Exception as e:
        debug_print(f"Vector RAG Store Search Runtime failure: {str(e)}")
        return f"Vector RAG Store Search Runtime failure: {str(e)}"

if __name__ == "__main__":
    # spin up the standard I/O communication gateway layer automatically
    mcp.run(transport="http", port=8000)