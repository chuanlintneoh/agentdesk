# Finance: Download Balance Sheet, Income Statement, Cash Flow tables from yfinance and save into local SQLite file for persistence
# Movie: Parse reviews, metadata, screenplay awards, and character tables from Kaggle dataset and save into local SQLite file for persistence
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import yfinance as yf
import pandas as pd
import pickle
from helper.debug import debug_print

def parse_yfinance_data(ticker: str = "AAPL") -> dict[str, pd.DataFrame]:
    ticker_clean = ticker.upper().strip()
    debug_print(f"Fetching {ticker_clean} financial statements...")
    
    # Fetch company's ticker data
    company = yf.Ticker(ticker_clean)
    
    # Extract structural dataframes
    income_stmt = company.income_stmt
    balance_sheet = company.balance_sheet
    cash_flow = company.cashflow
    
    # Transpose so dates are rows and metrics are columns
    df_income = income_stmt.T
    df_balance = balance_sheet.T
    df_cash = cash_flow.T
    
    # Clean the index (dates) to be a normal column
    df_income.index.name = "Date"
    df_income = df_income.reset_index()
    df_income["Date"] = df_income["Date"].astype(str)
    
    df_balance.index.name = "Date"
    df_balance = df_balance.reset_index()
    df_balance["Date"] = df_balance["Date"].astype(str)
    
    df_cash.index.name = "Date"
    df_cash = df_cash.reset_index()
    df_cash["Date"] = df_cash["Date"].astype(str)

    return {
        "income_statements": df_income,
        "balance_sheets": df_balance,
        "cash_flows": df_cash
    }

def parse_movie_dataset(dataset_path: str = ".tmp/movies/movie-scripts-corpus") -> dict[str, pd.DataFrame]:
    # https://www.kaggle.com/datasets/gufukuro/movie-scripts-corpus
    metadata_dir = os.path.join(dataset_path, "movie_metadata")
    if not os.path.exists(metadata_dir):
        raise FileNotFoundError(f"Missing dataset path: '{metadata_dir}'")
    
    df_reviews = None
    df_movies = None
    df_awards = None
    df_characters = None
    
    reviews_file = os.path.join(metadata_dir, "metacritic_reviews_cut_versions.csv")
    metadata_file = os.path.join(metadata_dir, "movie_meta_data.csv")
    awards_file = os.path.join(metadata_dir, "screenplay_awards.csv")
    characters_file = os.path.join(dataset_path, "movie_characters", "data", "character_genders.pickle")
    if os.path.exists(reviews_file):
        df_reviews = pd.read_csv(reviews_file)
        df_reviews.columns = df_reviews.columns.str.strip().str.lower()
    if os.path.exists(metadata_file):
        df_movies = pd.read_csv(metadata_file)
        df_movies.columns = df_movies.columns.str.strip().str.lower()
    if os.path.exists(awards_file):
        df_awards = pd.read_csv(awards_file)
        df_awards.columns = df_awards.columns.str.strip().str.lower()
    if os.path.exists(characters_file):
        try:
            with open(characters_file, "rb") as pf:
                gender_data = pickle.load(pf)
            
            records = []
            if isinstance(gender_data, dict):
                for char_key, metadata in gender_data.items():
                    # Handle both flat strings and dynamic sub-dictionaries inside the pickle file
                    if isinstance(metadata, dict):
                        record = {"character_key": char_key, **metadata}
                    else:
                        record = {"character_key": char_key, "gender": metadata}
                    for key, value in list(record.items()):
                        if isinstance(value, (list, dict, tuple)):
                            record[key] = str(value)
                    records.append(record)
            if records:
                df_characters = pd.DataFrame(records)
                df_characters.columns = df_characters.columns.str.strip().str.lower()
        except Exception as e:
            debug_print(f"Failed to load character genders: {str(e)}")
    
    return {
        "reviews": df_reviews,
        "movies": df_movies,
        "awards": df_awards,
        "characters": df_characters
    }

def save_to_sqlite(dfs: dict[str, pd.DataFrame], db: str = "./data/agentdesk_sqlite.db"):
    debug_print(f"Connecting to SQLite database ('{db}')...")
    conn = sqlite3.connect(db)
    
    # Write tables to SQLite
    for table_name, df in dfs.items():
        if df is not None:
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            debug_print(f"Table '{table_name}' written to SQLite database.")
        else:
            debug_print(f"DataFrame for '{table_name}' is None. Skipping table creation.")
    
    conn.close()
    debug_print(f"SQLite database setup completed and connection closed ('{db}').")

def setup_finance_sql(ticker: str, db: str = "./data/agentdesk_sqlite.db"):
    dfs = parse_yfinance_data(ticker=ticker)
    save_to_sqlite(dfs=dfs, db=db)

def setup_movies_sql(dataset_path: str = ".tmp/movies/movie-scripts-corpus", db: str = "./data/agentdesk_sqlite.db"):
    dfs = parse_movie_dataset(dataset_path=dataset_path)
    save_to_sqlite(dfs=dfs, db=db)