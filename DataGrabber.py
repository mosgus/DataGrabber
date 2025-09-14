import time
import datetime
from YF import (
    get_tickers, validate_tickers, has_data, get_CSV_dates,
    update_setup, validate_CSV_data, t0_interpret  # if you want flexible date parsing
)

def YF():
    # 1) Collect and validate symbols
    symbols = get_tickers()
    valid, invalid = validate_tickers(symbols)
    if not valid:
        print("No valid symbols entered. Exiting.")
        return

    # First pass: show status (and print CSV vs YF once here)
    any_csv = False
    cached_ranges = {}   # symbol -> (dateA, dateZ)
    is_valid_map = {}    # symbol -> bool

    for symbol in valid:
        if has_data(symbol):
            any_csv = True
            dateA, dateZ = get_CSV_dates(symbol)
            cached_ranges[symbol] = (dateA, dateZ)
            print(f"Data from {dateA} to {dateZ} for {symbol}.csv exists in /data")

            # Validate ONCE here (this prints the comparison frames)
            is_valid = validate_CSV_data(dateA, dateZ, symbol)
            is_valid_map[symbol] = is_valid

            if is_valid:
                print("Cached CSV is VALID.")
            else:
                print("Cached CSV is INVALID and will be replaced if you choose to update.")
        else:
            print(f"No cached CSV for {symbol}.")
            # default to False for symbols without a file (so update triggers full refresh)
            is_valid_map[symbol] = False

    # Global decision and shared date input
    if any_csv:
        choice = input("Update the CSV file(s)? (y/n): ").strip().lower()
        if choice not in ("y", "yes"):
            print("Exiting without updating.")
            return
        # Optional: flexible parsing like '25 1 1'
        newDateA_raw = input("Enter NEW base date for all symbols (YYYY-MM-DD or 'YY M D'): ").strip()
        newDateA = t0_interpret(newDateA_raw).strftime("%Y-%m-%d")
    else:
        newDateA_raw = input("Enter base date for all symbols (YYYY-MM-DD or 'YY M D'): ").strip()
        newDateA = t0_interpret(newDateA_raw).strftime("%Y-%m-%d")

    newDateZ = datetime.datetime.today().strftime("%Y-%m-%d")

    # Second pass: perform updates WITHOUT calling validate again
    for symbol in valid:
        if symbol in cached_ranges:
            dateA, dateZ = cached_ranges[symbol]
        else:
            # No CSV existed; pass placeholders so update_setup has something for the signature
            dateA, dateZ = newDateA, newDateA

        update_setup(
            dateA, dateZ,          # current cached range (or placeholder)
            newDateA, newDateZ,    # target span (shared)
            symbol,
            is_valid_map[symbol]   # CHANGED: pass the first-pass result so update_setup won't re-validate
        )

def main():
    pass

if __name__ == "__main__":
    YF()
    # main()