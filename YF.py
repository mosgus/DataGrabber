# YF.py
"""
Conceived on Mon Sep 8 2025
Birthed on
@author: Gunnar B.
"""

'''
This script prompts the user to input stock ticker symbols separated by commas.
Each individual ticker is extracted and used to fetch stock data from Yahoo Finance.
Stock data is processed and saved as CSV files for further analysis.
'''
import datetime
import yfinance as yf
import pandas as pd
import os
import shutil

import numpy as np

import time # for sleep() aesthetic pauses

''' ticker inputs'''
def get_tickers():
    tickers = input ("Enter stock ticker(s) separated by commas: ").upper()
    ticker_list = [t.strip() for t in tickers.split(',') if t.strip()] # Separate tickers based on comma
    return ticker_list
''' date inputs'''
def t0_interpret(t0_str):
    t0_str = t0_str.replace(' ', '-')
    parts = t0_str.split('-')
    if len(parts) == 3 and len(parts[0]) == 2:
        year = int(parts[0])
        if year > 25:
            year += 1900
        else:
            year += 2000
        t0_str = f"{year:04d}-{parts[1]}-{parts[2]}"
    return datetime.datetime.strptime(t0_str, "%Y-%m-%d")
def get_dates(prompt=""):
    while True:
        t0_str = input(prompt)
        try:
            t0 = t0_interpret(t0_str) # Interpret the input date
            tn = datetime.datetime.today() - datetime.timedelta(days=1)
            if t0 > tn:
                print("Invalid date. Can't look into the future bub.")
                continue
            return t0.strftime("%Y-%m-%d"), tn.strftime("%Y-%m-%d")
            # remove .strftime("%Y-%m-%d") to also return time, but yfinance only needs date
        except ValueError:
            print("Bad format. Use YYYY-MM-DD.")
''' validate symbols/tickers'''
def validate_ticker(ticker):
    try:
        ticker = yf.Ticker(ticker)
        info = ticker.info
        return True if info.get('regularMarketPrice') else False
    except:
        return False
def validate_tickers(symbols):
    print("Validating all ticks")
    valid_ticks = []
    invalid_ticks = []
    for symbol in symbols:
        if validate_ticker(symbol):
            valid_ticks.append(symbol)
        else:
            invalid_ticks.append(symbol)
    if invalid_ticks:
        print(f"ERROR: Invalid symbol(s) --> {invalid_ticks}")
    if valid_ticks:  # If we have at least one valid symbol, proceed
        print(f"Accepted symbols: {valid_ticks}")
    else:
        print("No valid symbols entered. Please try again.")
    return valid_ticks, invalid_ticks


''' Check if ticker data EXISTS in /data '''
def has_data(symbol):
    #filename = os.path.join("data", f"{symbol}.csv")
    #return os.path.isfile(filename)
    return os.path.isfile(os.path.join("data", f"{symbol}.csv"))
''' Fetch date range for EXISTING ticker '''
def get_CSV_dates(symbol):
    filename = os.path.join("data", f"{symbol}.csv")
    df = pd.read_csv(filename)
    df['Date'] = pd.to_datetime(df['Date'])
    t0 = df['Date'].min().strftime("%Y-%m-%d")
    tn = df['Date'].max().strftime("%Y-%m-%d")
    return t0, tn

''' Fetch data for NEW ticker '''
def fetch_data(symbol, t0, tn):
    df = yf.download(symbol, start=t0, end=tn, auto_adjust=False) # FYI auto_adjust for dividends and splits makes Adj Close redundant data.
    return df
''' Save data as NEW CSV file '''
def save_data(df, symbol):
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)  # Get first level of column names

        df = df.reset_index()  # Make 'Date' a column
        expected_columns = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        available_columns = [col for col in expected_columns if col in df.columns]
        df = df[available_columns]
        os.makedirs("data", exist_ok=True)
        filename = os.path.join("data", f"{symbol}.csv")
        df.to_csv(filename, index=False, header=True)
        print(f"{filename} saved...")
    else:
        print(f"No data found for {symbol}, in given date range.")

''' Handling EXISTING data '''
def cp_del(csv_path: str, symbol: str) -> str:
    """
    Copy csv_path to a timestamped *_OLD.csv, then delete the original.
    Returns the backup file path.
    """
    folder = os.path.dirname(csv_path)
    backup_name = f"{symbol}_OLD.csv"
    backup_path = os.path.join(folder, backup_name)
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Source CSV not found: {csv_path}") # Make sure source exists
    shutil.copy2(csv_path, backup_path)  # Copy with metadata
    os.remove(csv_path) # Remove original
    return backup_path

def validate_CSV_data(dateA, dateZ, symbol):
    """
    Compares CSV close and adj close prices for all quarters between
    dateA and dateZ with current Yahoo Finance data for the same quarters.
    Practically speaking Adj Close is the only one that matters, but Close
    does rarely get corrupted or edited too, so it's worth as a safeguard.
    """
    csv_path = os.path.join("data", f"{symbol}.csv")
    print(f"Validating data in {csv_path} from {dateA} to {dateZ}...")
    start_date = pd.to_datetime(dateA)
    end_date = pd.to_datetime(dateZ)

    # --- Just use dateA instead of multiple quarters ---
    check_date = pd.to_datetime(dateA).normalize()
    check_dates = pd.DatetimeIndex([check_date])

    # --- CSV Data ---
    csv_df = pd.read_csv(csv_path, parse_dates=["Date"])
    csv_df.set_index("Date", inplace=True)
    print(f"Prices in {symbol}.csv:")
    csv_data = csv_df.loc[csv_df.index.intersection(check_dates), ["Close", "Adj Close"]]
    print(csv_data) # 🖨️

    # --- Yahoo Finance Data ---
    yf_df = yf.download(symbol,start=start_date,end=end_date,auto_adjust=False,group_by="column", progress=False)
    # Just for formatting aesthetics. Removes ticker row if present
    if isinstance(yf_df.columns, pd.MultiIndex):
        try: # Prefer cross-section by ticker; if level name differs, use level index -1
            yf_df = yf_df.xs(symbol, axis=1, level=1)
        except Exception:
            yf_df.columns = yf_df.columns.get_level_values(0)
    yf_df = yf_df[["Close", "Adj Close"]].copy()
    yf_df.index = pd.to_datetime(yf_df.index).normalize()
    yf_df = yf_df.sort_index()
    print(f"Current {symbol} YF prices:")
    yf_data = yf_df.loc[yf_df.index.intersection(check_dates)]
    print(yf_data) # 🖨️

    # --- Check if data matches ---
    csv_data = csv_data.sort_index()
    yf_data = yf_data.sort_index()

    csv_adj = csv_data["Adj Close"].astype(float)
    yf_adj = yf_data["Adj Close"].astype(float)

    tolerance = 0.000001  # tighten as needed, or set to 0.01 for 1 cent
    comparison = np.isclose(
        csv_adj,
        yf_adj,
        atol=tolerance,
        rtol=0.0  # 🔑 disable relative tolerance
    )
    all_match = bool(comparison.all())

    if all_match:
        print(f"Data in {symbol}.csv is VALID by +/- {tolerance}.")
        return True
    else: # Copy's old date as "<symbol>OLD.csv" and prepares new file.
        print(f"Data in {symbol}.csv is NOT VALID by +/- {tolerance}.")
        backup_path = cp_del(csv_path, symbol)
        print(f"Old data copied to {backup_path} and removed {csv_path}.")
        return False


''' Get next trading day after given date '''
import pandas_market_calendars as mcal
nyse = mcal.get_calendar("NYSE")
def get_next_trading_day(date):
    d = pd.to_datetime(date)                          # convert str -> Timestamp
    schedule = nyse.schedule(start_date=d, end_date=d + pd.Timedelta(days=7))
    if schedule.empty:
        raise ValueError(f"No trading days on or after {date}")
    return schedule.index.min().date()                # or .strftime("%Y-%m-%d")
def get_last_trading_day(date):
    d = pd.to_datetime(date)
    schedule = nyse.schedule(start_date=d - pd.Timedelta(days=7), end_date=d)
    if schedule.empty:
        raise ValueError(f"No trading days on or before {date}")
    return schedule.index.max().date()

''' Setup for updating existing data'''
def update_setup(dateA, dateZ, newDateA, newDateZ, symbol):
    print(f"Updating {symbol}.csv...")
    #print(f"old range: {dateA} to {dateZ}")
    #print(f"new range: {newDateA} to {newDateZ}")

    if validate_CSV_data(dateA, dateZ, symbol):
        ''' VALID CSV DATA '''
        # Fo nearest valid trading days. This is just for aesthetic prints.
        tDateA = get_next_trading_day(newDateA)      # returns a date
        tDateZ = get_last_trading_day(newDateZ)      # returns a date
        tDateA_str = pd.to_datetime(tDateA).strftime("%Y-%m-%d")
        tDateZ_str = pd.to_datetime(tDateZ).strftime("%Y-%m-%d")

        if (dateA == tDateA_str and dateZ == tDateZ_str):
            print(f"No update needed for {symbol}.csv. Dates match.")
            return
        else:
            print(f"Getting more data...")
            print(f"\nNext trade day from {newDateA} = {tDateA_str}.\nLast trade day from {newDateZ} = {tDateZ_str}.")
            # TODO:

    else:
        ''' INVALID CSV DATA '''
        # also adjust dates when invalid
        tDateA = get_next_trading_day(newDateA)
        tDateZ = get_last_trading_day(newDateZ)
        tDateA_str = pd.to_datetime(tDateA).strftime("%Y-%m-%d")
        tDateZ_str = pd.to_datetime(tDateZ).strftime("%Y-%m-%d")
        print(f"Fetching NEW data for {symbol} from {tDateA_str} to {tDateZ_str}...")
        end_exclusive = (pd.to_datetime(tDateZ_str) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        df_new = fetch_data(symbol, newDateA, end_exclusive)
        save_data(df_new, symbol)