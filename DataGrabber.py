# DataGrabber.py

import time # for sleep() aesthetic pauses

from YF import (
    get_tickers,
    validate_tickers,
    has_data,
    get_CSV_dates,
    get_dates,
    update_setup,
    fetch_data,
    save_data
)

def YF():
    """
    Main function to drive the data grabbing process.
    """
    while True:
        symbols = get_tickers()

        time.sleep(0.25)

        if not symbols:
            continue
        valid_ticks, invalid_ticks = validate_tickers(symbols)
        if valid_ticks:
            break

    symbols = valid_ticks.copy()
    active_symbols = symbols[:]

    time.sleep(0.5)

    for i, symbol in enumerate(symbols):
        if has_data(symbol):
            dateA, dateZ = get_CSV_dates(symbol)
            print(f"Data from {dateA} to {dateZ} for {symbol}.csv exists in /data")

            time.sleep(0.5)

            while True:
                sino = input(f"Update {symbol}.csv? (y/n): ").lower()
                if sino in ['y', 'n']:
                    break
                print("Enter 'y' or 'n'.")

            if sino == 'n':
                active_symbols.remove(symbol)
                print(f"Ignoring {symbol}.")

                time.sleep(0.5)

            if sino == 'y':
                active_symbols.remove(symbol)
                prompt = f"Enter {symbol}.csv's NEW base date (YYYY-MM-DD): "
                newDateA, newDateZ = get_dates(prompt)

                time.sleep(1)

                print(f"{symbol}.csv will update data from {newDateA} to {newDateZ}")

                update_setup(dateA, dateZ, newDateA, newDateZ, symbol)

    if not active_symbols:
        print("\ndone.")
        return

    time.sleep(1)

    prompt = f"Enter base date for {active_symbols} (YYYY-MM-DD): "
    t0, tn = get_dates(prompt)
    print(f"Date Range for new symbols: {t0} to {tn}")

    time.sleep(1)
    for symbol in active_symbols:
        print(f"Fetching data for {symbol}...")
        df = fetch_data(symbol, t0, tn)
        save_data(df, symbol)

def main():
    choice = input(f"Run YF Data Grabber? (y/n): ").lower()
    if choice == 'y':
        YF()
    else:
        print("Exiting...")


if __name__ == "__main__":
    YF()
