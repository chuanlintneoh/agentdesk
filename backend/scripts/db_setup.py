import os
from db_sql import setup_sql
from db_vector import setup_vector

if __name__ == "__main__":
    TICKER = "AAPL"
    os.makedirs("data", exist_ok=True)

    print("Setting up SQL database...")
    setup_sql(ticker=TICKER, db="./data/agentdesk.db")
    print("SQL database setup successfully!\n")

    print("Setting up Vector database...")
    setup_vector(ticker=TICKER, db="./data/chroma_db")
    print("Vector database setup successfully!\n")