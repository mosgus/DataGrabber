import time  # for sleep() aesthetic pauses
import datetime
from YF import (get_tickers, validate_tickers, has_data, get_CSV_dates,update_setup, validate_CSV_data, t0_interpret)

def YF():
    # 1) Collect tickers and validate symbols
    symbols = get_tickers()
    valid, invalid = validate_tickers(symbols)
    if not valid:
        print("No valid symbols entered. Exiting.")
        return

    # -------- First pass: inspect/validate what exists (no prompts yet) --------
    any_csv = False
    cached_ranges = {}      # symbol -> (dateA, dateZ) for symbols that DO have CSVs
    is_valid_map = {}       # symbol -> bool; False for symbols with NO CSV  # CHANGED

    for symbol in valid:
        if has_data(symbol):
            any_csv = True
            dateA, dateZ = get_CSV_dates(symbol)
            cached_ranges[symbol] = (dateA, dateZ)
            print(f"{dateA} to {dateZ} data for {symbol}.csv exists in /data")

            # validate & print comparison ONCE here
            is_valid = validate_CSV_data(dateA, dateZ, symbol)
            is_valid_map[symbol] = is_valid
            if is_valid:
                print("Cached CSV is VALID.")
            else:
                print("Cached CSV is INVALID and will be replaced if you choose to update.")
        else:
            print(f"No cached CSV for {symbol}.")
            is_valid_map[symbol] = False  # CHANGED: mark as invalid so update does a full refresh

    # -------- Global decision + single shared base date --------
    if any_csv:
        choice = input("Update the CSV file(s)? (y/n): ").strip().lower()
        if choice not in ("y", "yes"):
            print("Exiting without updating.")
            return
        newDateA_raw = input("Enter NEW base date for all symbols (YYYY-MM-DD or 'YY M D'): ").strip()
        newDateA = t0_interpret(newDateA_raw).strftime("%Y-%m-%d")
    else:
        # No CSVs at all → still need a base date to build fresh files
        newDateA_raw = input("Enter base date for all symbols (YYYY-MM-DD or 'YY M D'): ").strip()
        newDateA = t0_interpret(newDateA_raw).strftime("%Y-%m-%d")

    newDateZ = datetime.datetime.today().strftime("%Y-%m-%d")

    # -------- Second pass: perform updates WITHOUT re-validating --------
    for symbol in valid:
        if symbol in cached_ranges:
            dateA, dateZ = cached_ranges[symbol]
        else:
            dateA, dateZ = newDateA, newDateA

        update_setup(
            dateA, dateZ,
            newDateA, newDateZ,
            symbol,
            is_valid_map[symbol]
        )

def main():
    pass

if __name__ == "__main__":
    YF()