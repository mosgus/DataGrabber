# Eikon(NA).py
import argparse
import sys
import pandas as pd
import os

import eikon as ek  # pip install eikon

def connect(api_key: str):
    ek.set_app_key(api_key)

def fetch_geo_revenue_region(ric: str, frq="FY", sdate="0", edate="-2") -> pd.DataFrame:
    fields = [
        "TR.BGS.GeoTotalRevenue.fperiod",
        "TR.BGS.GeoTotalRevenue.segmentName",
        "TR.BGS.GeoTotalRevenue",
        "TR.CompanyName",
    ]
    params = {"Frq": frq, "SDate": sdate, "EDate": edate}
    df, err = ek.get_data(ric, fields, params)
    if err:
        raise RuntimeError(err)
    # Standardize column names
    df = df.rename(columns={
        "Geographic Total Revenues (Calculated)": "Revenue",
        "Segment Name": "Segment",
        "TR.BGS.GeoTotalRevenue.fperiod": "FPeriod",
        "Company Name": "Company",
    })
    # Drop totals that the API includes
    mask = ~df["Segment"].isin(["Segment Total", "Consolidated Total"])
    df = df[mask]
    return df

def resolve_to_ric(symbol: str) -> str:
    """
    Resolve a user input ticker to a valid RIC.
    If already looks like a RIC (has a '.'), return as-is.
    """
    if "." in symbol:
        return symbol  # assume it's already a RIC
    try:
        df, err = ek.get_symbology(symbol, from_symbol_type="ticker", to_symbol_type="RIC")
        if err:
            print(f"Symbology error: {err}")
            return symbol
        if not df.empty and "RIC" in df.columns:
            return df["RIC"].iloc[0]
    except Exception as e:
        print(f"Symbology lookup failed: {e}")
    # Fallback: guess Nasdaq
    return symbol + ".O"

def main():
    p = argparse.ArgumentParser(description="Revenue by Region, last 2 FY by default")
    p.add_argument("key", help="Eikon API app key")
    p.add_argument("ticker", help="RIC or ticker, e.g., AAPL.O")
    p.add_argument("metric", nargs="?", default="Revenue")
    args = p.parse_args()

    try:
        connect(args.key) # Eikon API connection
        ric = resolve_to_ric(args.ticker) # resolve user input ticker to a RIC
        df = fetch_geo_revenue_region(ric, frq="FY", sdate="0", edate="-2") # fetch geographic revenue data
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if df.empty:
        print("No geographic revenue rows were returned.")
        sys.exit(0)

    # Show preview: head(3) and tail(3)
    print("\n--- DataFrame head(3) ---")
    print(df.head(3).to_string(index=False))
    print("\n--- DataFrame tail(3) ---")
    print(df.tail(3).to_string(index=False))

    # Save CSV into /data directory
    os.makedirs("data", exist_ok=True)
    filename = f"data/{args.ticker}_revenue_region.csv"
    df.to_csv(filename, index=False)
    print(f"\nSaved full dataset to {filename}")

    # Optional: still print grouped by fiscal period
    for fper, grp in df.groupby("FPeriod", dropna=False):
        print(f"\nFiscal period: {fper}")
        print(grp[["Segment", "Revenue"]].to_string(index=False))

if __name__ == "__main__":
    main()