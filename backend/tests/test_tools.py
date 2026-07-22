from tools import (
    get_database_blueprint,
    execute_sql_query,
    list_vector_collections,
    retrieve_text_context
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
        "CREATE TABLE test (id INT);"
    ]
    for query in forbidden_queries:
        res = execute_sql_query(query)
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
