# YF.py
"""
    Conceived on Mon Sep 8 2025
    Birthed on
    @author: Gunnar B.

    This script prompts the user to input stock ticker symbols separated by commas.
    Each individual ticker is extracted and used to fetch stock data from Yahoo Finance.
    Stock data is processed and saved as CSV files for further analysis.
"""

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
        print(f"Accepted symbols: {valid_ticks}\n")
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
    df = yf.download(symbol, start=t0, end=tn, auto_adjust=False, progress=False) # FYI auto_adjust is for splits/divs. Progress is the red printed msg.
    return df
''' Save data as NEW CSV file '''
def save_data(df, symbol):
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)  # flatten

        df = df.reset_index()
        expected = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        keep = [c for c in expected if c in df.columns]
        df = df[keep]

        os.makedirs("data", exist_ok=True)
        filename = os.path.join("data", f"{symbol}.csv")
        tmpname = os.path.join("data", f".{symbol}.csv.tmp")

        # Write with high precision so 1e-5 deltas survive round-trip
        df.to_csv(tmpname, index=False, header=True, float_format="%.14f")

        os.replace(tmpname, filename)  # atomic on POSIX
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
    print(f"Validating data in {csv_path} from {dateA} to {dateZ}...\n")
    start_date = pd.to_datetime(dateA)
    end_date = pd.to_datetime(dateZ)
    # Just check one date in the range
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

    tolerance = 0.000001  # tighten as needed 🔑
    comparison = np.isclose(csv_adj, yf_adj, atol=tolerance, rtol=0.0)
    all_match = bool(comparison.all())

    if all_match:
        print(f"\nAdj_Price in {symbol}.csv is VALID by +/- {tolerance} minimum.")
        return True
    else: # Copy's old date as "<symbol>OLD.csv" and prepares new file.
        print(f"\nAdj_Price in {symbol}.csv is OUTDATED by +/- {tolerance} minimum.")
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
''' Handle data prepending and/or appending '''
def datapend(dateA, dateZ, tDateA, tDateZ, symbol):
    """
    Given the current CSV range [dateA, dateZ] and the desired trading-day-aligned
    range [tDateA, tDateZ], fetch only the missing edges and stitch them onto the
    existing CSV in /data/<symbol>.csv.

    Cases:
      - If dateA == tDateA and dateZ == tDateZ -> nothing to do (should be handled earlier).
      - If dateA == tDateA -> append only.
      - If dateZ == tDateZ -> prepend only.
      - Else -> prepend and append.
    """
    csv_path = os.path.join("data", f"{symbol}.csv")
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Expected existing CSV at {csv_path}")

    # Load existing file
    csv_df = pd.read_csv(csv_path, parse_dates=["Date"])
    csv_df = csv_df.sort_values("Date").reset_index(drop=True)

    # Normalize inputs to strings (YYYY-MM-DD)
    dateA = pd.to_datetime(dateA).strftime("%Y-%m-%d")
    dateZ = pd.to_datetime(dateZ).strftime("%Y-%m-%d")
    tDateA = pd.to_datetime(tDateA).strftime("%Y-%m-%d")
    tDateZ = pd.to_datetime(tDateZ).strftime("%Y-%m-%d")

    need_prepend = (dateA != tDateA)
    need_append  = (dateZ != tDateZ)

    prepend_df = pd.DataFrame()
    append_df  = pd.DataFrame()

    #   yfinance 'end' is exclusive.
    #   PREPEND: [tDateA, dateA-1]  -> fetch_data(symbol, tDateA, end_exclusive=dateA)
    #   APPEND:  [dateZ+1, tDateZ]  -> fetch_data(symbol, start_inclusive=dateZ_plus1, end_exclusive=tDateZ_plus1)

    if need_prepend:
        end_exclusive = pd.to_datetime(dateA).strftime("%Y-%m-%d")
        prepend_df = fetch_data(symbol, tDateA, end_exclusive)

    if need_append:
        start_inclusive = (pd.to_datetime(dateZ) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        end_exclusive = (pd.to_datetime(tDateZ) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        append_df = fetch_data(symbol, start_inclusive, end_exclusive)

    # Normalize fetched frames to match CSV schema
    def _tidy(df):
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        cols = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        keep = [c for c in cols if c in df.columns]
        return df[keep]

    prepend_df = _tidy(prepend_df)
    append_df  = _tidy(append_df)

    # Concatenate [prepend, existing, append], drop dups, sort, save back to /data/<symbol>.csv
    combined = pd.concat([prepend_df, csv_df, append_df], ignore_index=True)
    # Drop duplicate dates if any overlap occurred
    if "Date" in combined.columns:
        combined["Date"] = pd.to_datetime(combined["Date"])
        combined = combined.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")

    os.makedirs("data", exist_ok=True)
    combined.to_csv(csv_path, index=False, float_format="%.6f")
    print(f"Stitched 'cached data' with 'new/additional data'\nsaved @ {csv_path}")
''' Setup for updating EXISTING csv data'''
def update_setup(dateA, dateZ, newDateA, newDateZ, symbol, is_valid_cached):
    print(f"\nHandling {symbol}.csv...")
    tDateA = get_next_trading_day(newDateA)
    tDateZ = get_last_trading_day(newDateZ)
    tDateA_str = pd.to_datetime(tDateA).strftime("%Y-%m-%d")
    tDateZ_str = pd.to_datetime(tDateZ).strftime("%Y-%m-%d")

    if is_valid_cached:
        ''' VALID CSV DATA '''
        if (dateA == tDateA_str and dateZ == tDateZ_str):
            print(f"No update needed for {symbol}.csv. Dates match.")
            return
        else:
            print(f"\nGetting more data...")
            print(f"Next trade day from {newDateA} = {tDateA_str}.\nLast trade day from {newDateZ} = {tDateZ_str}.")
            # Only stitch if the cache exists and is valid
            datapend(dateA, dateZ, tDateA_str, tDateZ_str, symbol)
    else:
        ''' INVALID or NO CSV DATA → full data grab '''
        print(f"Fetching NEW {symbol} data from {tDateA_str} to {tDateZ_str}...")
        end_exclusive = (pd.to_datetime(tDateZ_str) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        df_new = fetch_data(symbol, tDateA_str, end_exclusive)

        if df_new is None or df_new.empty:
            print(f"New fetch for {symbol} returned no rows. Aborting replace; keeping existing files.")
            return

        # Keep previous CSV in memory for a precise delta print
        csv_path = os.path.join("data", f"{symbol}.csv")
        old_df = None
        if os.path.exists(csv_path):
            try:
                old_df = pd.read_csv(csv_path, parse_dates=["Date"]).set_index("Date")
            except Exception:
                old_df = None

        # Back up AFTER a successful fetch
        if os.path.exists(csv_path):
            backup_path = cp_del(csv_path, symbol)
            print(f"Backed up old CSV to {backup_path}")

        # Save new with high precision (save_data uses float_format="%.9f")
        save_data(df_new, symbol)

        # --- Post-save verification at the anchor date ---
        try:
            new_df = pd.read_csv(csv_path, parse_dates=["Date"]).set_index("Date")
            # Use the same anchor you validated on: the cached file’s dateA if it existed,
            # otherwise the new tDateA (for the first file ever).
            anchor = pd.to_datetime(dateA) if old_df is not None else pd.to_datetime(tDateA_str)

            if anchor in new_df.index:
                new_adj = float(new_df.loc[anchor, "Adj Close"])
                if old_df is not None and anchor in old_df.index:
                    old_adj = float(old_df.loc[anchor, "Adj Close"])
                    delta = new_adj - old_adj
                    print(f"\nPost-save check @ {anchor.date()}: old Adj={old_adj:.9f}, new Adj={new_adj:.9f}, Δ={delta:.9f}")
                else:
                    print(f"\nPost-save check @ {anchor.date()}: new Adj={new_adj:.9f}")
            else:
                print(f"\nPost-save check: anchor {anchor.date()} is not in the new CSV (start date changed).")
        except Exception as e:
            print(f"\nPost-save check skipped: {e}")
# =========================
# CLI entrypoint (non-breaking)
# =========================
import argparse

def m_parse_cli_args():
    p = argparse.ArgumentParser(
        prog="YF.py",
        description="Yahoo Finance data grabber: single-ticker CLI mode."
    )
    p.add_argument("ticker", help="Ticker symbol, e.g., NVDA")
    p.add_argument(
        "start_date",
        nargs="?",
        help="Optional start date YYYY-MM-DD. If omitted, uses YTD only when no CSV exists; otherwise append-only."
    )
    return p.parse_args()

def m_ytd_start_today():
    today = datetime.datetime.today().date()
    ytd_start = datetime.date(today.year, 1, 1)
    end = today - datetime.timedelta(days=1)
    return ytd_start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def m_normalize_start_date(start_date_str):
    dt = t0_interpret(start_date_str)
    return dt.strftime("%Y-%m-%d")

def m_cli_update_one(ticker, start_date_opt):
    valid, invalid = validate_tickers([ticker.upper()])
    if not valid:
        print("No valid symbols. Exiting.")
        return
    symbol = valid[0]

    csv_exists = has_data(symbol)
    if csv_exists:
        # Existing CSV: only append from last CSV date + 1 to last trading day
        dateA, dateZ = get_CSV_dates(symbol)
        is_valid_cached = True  # leverage your existing CSV validation upstream if desired

        if start_date_opt:
            # Rule 2 in your spec: only update if the provided start does NOT overlap CSV.
            newDateA = m_normalize_start_date(start_date_opt)
            if newDateA <= dateZ:
                print(
                    f"Requested start {newDateA} overlaps existing {symbol}.csv range "
                    f"[{dateA}..{dateZ}]. Skipping update."
                )
                return
            newDateZ = (datetime.datetime.today().date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            # Use m_update_setup to guard against accidental prepend
            m_update_setup(dateA, dateZ, newDateA, newDateZ, symbol, is_valid_cached)
        else:
            # No explicit start given: DO NOT use YTD. Append only.
            newDateA = (pd.to_datetime(dateZ) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            newDateZ = (datetime.datetime.today().date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            m_update_setup(dateA, dateZ, newDateA, newDateZ, symbol, is_valid_cached)
    else:
        # No CSV yet: use start_date if provided; else YTD
        if start_date_opt:
            newDateA = m_normalize_start_date(start_date_opt)
        else:
            newDateA, _ytdZ = m_ytd_start_today()
        newDateZ = (datetime.datetime.today().date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        # No cached file exists, so tell updater to do a full grab
        # We pass dateA/dateZ as equal to newDateA so m_update_setup treats as fresh
        m_update_setup(newDateA, newDateA, newDateA, newDateZ, symbol, is_valid_cached=False)

# --- m_* copies that are safer for CLI append-only semantics ---

def m_update_setup(dateA, dateZ, newDateA, newDateZ, symbol, is_valid_cached):
    """
    Safer wrapper that only prepends when new target start < existing dateA,
    and only appends when new target end > existing dateZ.
    """
    print(f"\nHandling {symbol}.csv...")
    tDateA = get_next_trading_day(newDateA)
    tDateZ = get_last_trading_day(newDateZ)
    tDateA_str = pd.to_datetime(tDateA).strftime("%Y-%m-%d")
    tDateZ_str = pd.to_datetime(tDateZ).strftime("%Y-%m-%d")

    if is_valid_cached:
        if (dateA == tDateA_str and dateZ == tDateZ_str):
            print(f"No update needed for {symbol}.csv. Dates match.")
            return
        else:
            print(f"\nGetting more data...")
            print(f"Next trade day from {newDateA} = {tDateA_str}.\nLast trade day from {newDateZ} = {tDateZ_str}.")
            m_datapend(dateA, dateZ, tDateA_str, tDateZ_str, symbol)
    else:
        print(f"Fetching NEW {symbol} data from {tDateA_str} to {tDateZ_str}...")
        end_exclusive = (pd.to_datetime(tDateZ_str) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        df_new = fetch_data(symbol, tDateA_str, end_exclusive)

        if df_new is None or df_new.empty:
            print(f"No data returned for {symbol} in requested range. Nothing saved.")
            return

        # Save fresh file using your existing normalizer and saver
        if isinstance(df_new.columns, pd.MultiIndex):
            df_new.columns = df_new.columns.get_level_values(0)
        df_new = df_new.reset_index()
        cols = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        keep = [c for c in cols if c in df_new.columns]
        df_new = df_new[keep]
        save_data(df_new, symbol)

def m_datapend(dateA, dateZ, tDateA, tDateZ, symbol):
    """
    Safer datapend:
      - Only prepend if tDateA < dateA
      - Only append  if tDateZ > dateZ
    Prevents reversed ranges like start > end.
    """
    csv_path = os.path.join("data", f"{symbol}.csv")
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Expected existing CSV at {csv_path}")

    csv_df = pd.read_csv(csv_path, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)

    dateA = pd.to_datetime(dateA)
    dateZ = pd.to_datetime(dateZ)
    tDateA = pd.to_datetime(tDateA)
    tDateZ = pd.to_datetime(tDateZ)

    need_prepend = tDateA < dateA
    need_append  = tDateZ > dateZ

    prepend_df = pd.DataFrame()
    append_df  = pd.DataFrame()

    if need_prepend:
        end_exclusive = (dateA).strftime("%Y-%m-%d")
        prepend_df = fetch_data(symbol, tDateA.strftime("%Y-%m-%d"), end_exclusive)

    if need_append:
        start_inclusive = (dateZ + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        end_exclusive   = (tDateZ + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        append_df = fetch_data(symbol, start_inclusive, end_exclusive)

    def _tidy(df):
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        cols = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        keep = [c for c in cols if c in df.columns]
        return df[keep]

    prepend_df = _tidy(prepend_df)
    append_df  = _tidy(append_df)

    # Merge parts
    combined = pd.concat([prepend_df, csv_df, append_df], ignore_index=True)
    if "Date" in combined.columns:
        combined["Date"] = pd.to_datetime(combined["Date"])
        combined = combined.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")

    os.makedirs("data", exist_ok=True)
    combined.to_csv(csv_path, index=False)
    print(f"Stitched 'cached data' with 'new/additional data'\nsaved @ {csv_path}")

def m_main_cli():
    import sys
    if len(sys.argv) <= 1:
        return
    args = m_parse_cli_args()
    m_cli_update_one(args.ticker, args.start_date)

if __name__ == "__main__":
    m_main_cli()