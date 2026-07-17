# Download Balance Sheet, Income Statement, Cash Flow tables from yfinance and save into local SQLite file for persistence
import sqlite3
import yfinance as yf

def download(ticker: str = "AAPL"):
    ticker_clean = ticker.upper().strip()
    print(f"Fetching {ticker_clean} financial statements...")
    
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

    return ticker_clean, df_income, df_balance, df_cash

def setup(ticker_clean: str, df_income, df_balance, df_cash, db: str = "./data/agentdesk.db"):
    db_clean = db.lower().strip()
    print(f"Connecting to SQLite database ('{db_clean}')...")
    conn = sqlite3.connect(db_clean)
    
    # Write tables to SQLite
    prefix = f"{ticker_clean.lower()}"
    df_income.to_sql(f"{prefix}_income_statement", conn, if_exists="replace", index=False)
    df_balance.to_sql(f"{prefix}_balance_sheet", conn, if_exists="replace", index=False)
    df_cash.to_sql(f"{prefix}_cash_flow", conn, if_exists="replace", index=False)
    
    print("SQL database populated! Created tables:")
    print(f"   - {prefix}_income_statement")
    print(f"   - {prefix}_balance_sheet")
    print(f"   - {prefix}_cash_flow")
    
    conn.close()

def setup_sql(ticker: str, db: str = "./data/agentdesk.db"):
    ticker_clean, df_income, df_balance, df_cash = download(ticker=ticker)
    setup(ticker_clean, df_income, df_balance, df_cash, db)