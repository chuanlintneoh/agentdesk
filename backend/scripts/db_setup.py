import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_sql import setup_finance_sql, setup_movies_sql
from db_vector import setup_corporate_vectordb, setup_movie_vectordb
from helper.debug import debug_print

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    TICKER = "AAPL"
    option = "A"

    if option == "A":
        setup_finance_sql(ticker=TICKER, db=f"./data/corporate{TICKER}_sqlite.db")
        setup_corporate_vectordb(ticker=TICKER, db=f"./data/corporate{TICKER}_chroma")
        setup_movies_sql(db="./data/movies_sqlite.db")
        # setup_movie_vectordb(db="./data/movies_chroma")
    elif option == "B":
        setup_finance_sql(ticker=TICKER, db="./data/agentdesk_sqlite.db")
        setup_corporate_vectordb(ticker=TICKER, db="./data/agentdesk_chroma")
    elif option == "C":
        setup_movies_sql(db="./data/agentdesk_sqlite.db")
        setup_movie_vectordb(db="./data/agentdesk_chroma")
    else:
        debug_print("Invalid option selected. Please choose 'A' or 'B' or 'C'.")