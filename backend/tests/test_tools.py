from tools import (
    get_database_blueprint,
    execute_sql_query,
    list_vector_collections,
    retrieve_text_context,
    fetch_external_api_data
)

def test_get_database_blueprint():
    # Should return string blueprint (either schema or empty message)
    result = get_database_blueprint()
    assert isinstance(result, str)
    assert len(result) > 0

def test_execute_sql_query_security():
    # Test forbidden SQL write operations
    forbidden_queries = [
        "DROP TABLE users;",
        "DELETE FROM users WHERE id = 1;",
        "UPDATE users SET name = 'test';",
        "INSERT INTO users (name) VALUES ('test');",
        "ALTER TABLE users ADD COLUMN age INT;",
        "CREATE TABLE test (id INT);",
        # Obfuscated / Case variants
        "dRoP TABLE users;",
        "DELETE/*comment*/FROM users;",
        "INSERT\nINTO users (name) VALUES ('test');",
        # Nested / Semicolon injection
        "SELECT 1; DROP TABLE users;",
        "SELECT 1-- DROP TABLE users"
    ]
    for query in forbidden_queries:
        res = execute_sql_query(query)
        assert "Security Restriction" in res

def test_fetch_external_api_data_security():
    # Test SSRF protection
    forbidden_urls = [
        "http://localhost:8000/health",
        "http://127.0.0.1/health",
        "http://backend:8000/health",
        "https://127.0.0.1.nip.io", # Hostname that resolves to 127.0.0.1
    ]
    for url in forbidden_urls:
        res = fetch_external_api_data(url)
        assert "Security Restriction" in res

def test_execute_sql_query_select():
    # Test a valid SELECT query or handled empty state
    res = execute_sql_query("SELECT 1;")
    assert isinstance(res, str)

def test_list_vector_collections():
    res = list_vector_collections()
    assert isinstance(res, str)
    assert "vector collections" in res.lower() or "empty" in res.lower()

def test_retrieve_text_context_nonexistent():
    res = retrieve_text_context("nonexistent_collection_12345", "test query")
    assert isinstance(res, str)
    assert "does not exist" in res or "Error" in res
