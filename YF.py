# YF.py
'''
This script prompts the user to input stock ticker symbols separated by commas.
Each individual ticker is extracted and used to fetch stock data from Yahoo Finance.
Stock data is processed and saved as CSV files for further analysis.
'''
import datetime
import yfinance as yf
import pandas as pd
import os

''' ticker inputs'''
def get_tickers():
    tickers = input ("Enter stock ticker(s) separated by commas: ")
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
def get_dates():
    while True:
        t0_str = input("Enter base date for new tick(s)(YYYY-MM-DD): ")
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


if __name__ == "__main__":
    while True:
        symbols = get_tickers()
        valid_ticks, invalid_ticks = validate_tickers(symbols) # Validate tickers
        if valid_ticks: # the loop needs to break somewhere
            break
    # while

    ''' Continue with valid symbols '''
    symbols = valid_ticks.copy()

    # Check for existing files
    for i, symbol in enumerate(symbols):
        if has_data(symbol):
            dateA, dateZ = get_CSV_dates(symbol)
            print(f"Data from {dateA} to {dateZ} for {symbol}.csv exists in /data")
            while True:
                sino = input(f"Update {symbol}.csv? (y/n): ").lower() # si or no?
                if sino in ['y', 'n']:
                    break
                print("Enter 'y' or 'n' idiot.")

            if sino == 'n':
                symbols[i] = f"|>"
                print(f"Ignoring {symbol}.")

            if sino == 'y':
                tick2update = symbols[i]
                symbols[i] = f"|>"

    # Check if any non-flagged symbols remain
        active_symbols = [s for s in symbols if not s.startswith("|>")]
        if not active_symbols:
            print("No symbols to fetch data for.")
            exit()

    t0, tn = get_dates()
    print(f"Date Range: {t0} to {tn}")

    for symbol in symbols:
        if symbol.startswith("|>"):  # Skip marked symbols
            continue
        print(f"Fetching data for {symbol}...")
        df = fetch_data(symbol, t0, tn)
        save_data(df, symbol)
# main