import re

# MOCK ENTERPRISE DATA STORE
# 1. Simulated SQL Database (Orders & Sales)
MOCK_SQL_DATABASE = {
    "orders": [
        {"order_id": "ORD001", "customer": "Acme Corp", "amount": 5000, "quarter": "Q3", "status": "Completed"},
        {"order_id": "ORD002", "customer": "Stark Tech", "amount": 12000, "quarter": "Q3", "status": "Refunded"},
        {"order_id": "ORD003", "customer": "Wayne Ent", "amount": 7500, "quarter": "Q3", "status": "Completed"},
        {"order_id": "ORD004", "customer": "LexCorp", "amount": 3000, "quarter": "Q4", "status": "Pending"}
    ]
}
# 2. Simulated Vector DB (Unstructured Documents)
MOCK_VECTOR_DB = [
    {
        "doc_id": "DOC_REFUND_POLICY",
        "title": "Corporate Refund & Returns Standard Operating Procedure",
        "content": "Company refund policy states that orders exceeding $10,000 are subject to an executive review panel before a refund can be processed. All Q3 refunds must be finalized by October 15th."
    },
    {
        "doc_id": "DOC_HR_BENEFITS",
        "title": "Employee Benefits Guide",
        "content": "Full-time employees are eligible for comprehensive health coverage, 20 days of annual leave, and annual wellness allowances."
    }
]

# MOCK MCP TOOLS
def query_sales_db(quarter: str) -> list:
    print(f"[Tool Execution] Running SQL Query for quarter: {quarter}")
    results = [order for order in MOCK_SQL_DATABASE["orders"] if order["quarter"] == quarter]
    return results

def search_corporate_policies(query: str) -> str:
    print(f"[Tool Execution] Scanning Vector DB for query: '{query}'")
    # Simple semantic keyword matching simulation
    keywords = query.lower().split()
    best_match = None
    max_matches = 0

    for doc in MOCK_VECTOR_DB:
        matches = sum(
            1 for kw in keywords if (
                (kw in doc["content"].lower()) or (kw in doc["title"].lower())
            )
        )
        if matches > max_matches:
            max_matches = matches
            best_match = doc
            
    if best_match:
        return f"Source: {best_match['title']}\nContent: {best_match['content']}"
    return "No matching corporate policy documents found."

def write_local_report(filename: str, report_content: str) -> str:
    print(f"[Tool Execution] Generating local system file: {filename}")
    try:
        # Sanitizing path for basic security simulation
        safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
        # In a real app, this writes to disk. We'll simulate success.
        return f"Successfully wrote report to filesystem as '{safe_filename}'."
    except Exception as e:
        return f"Failed to write file: {str(e)}"