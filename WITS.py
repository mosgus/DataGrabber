"""
WITS.py — modular CLI skeleton for querying World Integrated Trade Solution (WITS)

Design goals
- Flexible, forgiving CLI that accepts specific or general inputs
- Normalizes countries, products (HS codes), years
- Builds narrowest valid API calls with sensible defaults
- Caches raw JSON and tidy CSV outputs
- Provides summarization utilities
- Mirrors the ergonomics of YF.py (CLI + caching)

NOTE: The exact WITS API routes and parameters can vary. Replace URL builders
with the official endpoints you plan to use. This file focuses on structure.
"""

from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import requests

# -------------------------------
# Constants and simple registries
# -------------------------------

APP_NAME = "WITS"
CACHE_DIR = os.path.join("data", "wits")
DEFAULT_TIMEOUT = 30
DEFAULT_LIMIT = 50000  # guardrail for very broad pulls
USER_AGENT = f"{APP_NAME}/0.1"

# Minimal ISO3 registry with common aliases. Extend as needed.
COUNTRY_ALIASES: Dict[str, str] = {
    # USA
    "usa": "USA", "us": "USA", "u.s.": "USA", "united states": "USA", "united states of america": "USA",
    # China
    "china": "CHN", "prc": "CHN", "chn": "CHN",
    # Canada
    "can": "CAN", "canada": "CAN",
    # Mexico
    "mex": "MEX", "mexico": "MEX",
    # United Kingdom
    "uk": "GBR", "u.k.": "GBR", "great britain": "GBR", "britain": "GBR", "united kingdom": "GBR", "gbr": "GBR",
    # Germany
    "de": "DEU", "germany": "DEU", "deu": "DEU",
    # France
    "fr": "FRA", "france": "FRA", "fra": "FRA",
    # Italy
    "it": "ITA", "italy": "ITA", "ita": "ITA",
    # Spain
    "es": "ESP", "spain": "ESP", "esp": "ESP",
    # Japan
    "jp": "JPN", "japan": "JPN", "jpn": "JPN",
    # South Korea
    "kr": "KOR", "south korea": "KOR", "republic of korea": "KOR", "korea": "KOR", "kor": "KOR",
    # Australia
    "au": "AUS", "australia": "AUS", "aus": "AUS",
    # India
    "in": "IND", "india": "IND", "ind": "IND",
    # Brazil
    "br": "BRA", "brazil": "BRA", "bra": "BRA",
    # Russian Federation
    "ru": "RUS", "russia": "RUS", "russian federation": "RUS", "rus": "RUS",
    # South Africa
    "za": "ZAF", "south africa": "ZAF", "zaf": "ZAF",
    # European Union
    "eu": "EUU", "european union": "EUU", "euu": "EUU",
    # World aggregate
    "world": "WLD", "wld": "WLD",
}

# -------------------------------
# Helpers: logging and file ops
# -------------------------------

def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_json(path: str, obj) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def write_csv(path: str, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# -------------------------------
# Normalization utilities
# -------------------------------

def normalize_country(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s_clean = re.sub(r"[^A-Za-z ]+", "", s).strip().lower()
    if s_clean in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[s_clean]
    # If user already provided ISO3-ish code
    if len(s.strip()) == 3 and s.strip().isalpha():
        return s.strip().upper()
    # Fallback: fuzzy suggest top 5 similar keys
    from difflib import get_close_matches
    matches = get_close_matches(s_clean, list(COUNTRY_ALIASES.keys()), n=5, cutoff=0.6)
    msg = f"Could not map '{s}'. Try ISO3 like 'USA' or common names."
    if matches:
        msg += f" Did you mean: {', '.join(sorted(set(COUNTRY_ALIASES[m] for m in matches)))}"
    raise ValueError(msg)


@dataclass
class HSProduct:
    scheme: str  # e.g., "HS"
    level: int   # 2, 4, or 6 typical
    code: str    # digits only string


def normalize_product(p: Optional[str]) -> Optional[HSProduct]:
    """Accepts formats like 'HS_85', '85', 'HS2:85', 'hs085', 'HS-85'.
    Returns HSProduct or None if not provided (meaning all products)."""
    if not p:
        return None
    raw = p.strip().upper()
    # strip common prefixes and separators
    raw = raw.replace("HS_", "HS").replace("HS-", "HS").replace("HS:", "HS").replace("HS ", "HS")
    m = re.match(r"^(HS)?(\d{2}|\d{4}|\d{6})$", raw)
    if not m:
        # Also allow plain numeric '85' or '8501' or '850110'
        m2 = re.match(r"^(\d{2}|\d{4}|\d{6})$", raw)
        if not m2:
            raise ValueError("Product must look like HS_85, 85, 8501, or 850110")
        digits = m2.group(1)
        return HSProduct("HS", len(digits), digits)
    digits = m.group(2)
    return HSProduct("HS", len(digits), digits)


@dataclass
class YearSpec:
    years: List[int]  # deduped, sorted


def normalize_years(year: Optional[int], years: Optional[str], start: Optional[int], end: Optional[int], latest: bool) -> YearSpec:
    out: List[int] = []
    if latest:
        return YearSpec(years=[])
    if year is not None:
        out.append(int(year))
    if years:
        for y in re.split(r"[, ]+", years.strip()):
            if y:
                out.append(int(y))
    if start is not None and end is not None:
        if end < start:
            raise ValueError("--end must be >= --start")
        out.extend(list(range(int(start), int(end) + 1)))
    out = sorted(sorted(set(out)))
    return YearSpec(out)

# -------------------------------
# Cache key and filenames
# -------------------------------

def cache_key(d: Dict[str, object]) -> str:
    blob = json.dumps(d, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def cache_paths(kind: str, keydict: Dict[str, object], base_dir: str = CACHE_DIR) -> Tuple[str, str]:
    """Returns (json_path, csv_path) for a given query key."""
    key = cache_key(keydict)
    folder = os.path.join(base_dir, kind)
    ensure_dir(folder)
    return os.path.join(folder, f"{key}.json"), os.path.join(folder, f"{key}.csv")

# -------------------------------
# HTTP with retry/backoff
# -------------------------------

def http_get_json(url: str, params: Optional[Dict[str, object]] = None, timeout: int = DEFAULT_TIMEOUT, max_retries: int = 3) -> dict:
    headers = {"User-Agent": USER_AGENT}
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout, headers=headers)
            if resp.status_code == 429:
                # Too many requests; back off
                wait = min(2 ** attempt, 30)
                log(f"429 received. Backing off {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_err = e
            wait = min(2 ** attempt, 10)
            log(f"Attempt {attempt} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"GET {url} failed after {max_retries} attempts: {last_err}")

# -------------------------------
# WITS URL builders (adjust to official API)
# -------------------------------
def build_trade_url(year: int, importer: str, partner: str, hs: Optional[HSProduct], indicator: str) -> str:
    """
    Build a tradestats-trade URL (SDMX V21 'datasource' style).
    - indicator: MPRT-TRD-VL (imports) or XPRT-TRD-VL (exports), etc.
    - product: use 'ALL' for reliable starts (WITS allows ALL with specific reporter/partner).
      You can later map HS to WITS product groups if desired.
    """
    product = "ALL" if hs is None else "ALL"  # keep ALL for a working start
    return (
        "https://wits.worldbank.org/API/V1/SDMX/V21/datasource/tradestats-trade/"
        f"reporter/{importer.lower()}/year/{year}/partner/{(partner or 'wld').lower()}/"
        f"product/{product}/indicator/{indicator}"
    )
def build_tariff_url(year: int, importer: str, partner: Optional[str], hs: Optional[HSProduct], indicator: str) -> str:
    """
    Build a tradestats-tariff URL (SDMX V21 'datasource' style).
    For a working default, use partner=WLD and product=fuels (doc example). You can generalize later.
    """
    partner_part = (partner or "WLD").lower()
    # For a guaranteed starter call, set product to 'fuels' (works in docs);
    # once you’re ready, wire hs -> a valid WITS product grouping.
    product = "fuels"
    return (
        "https://wits.worldbank.org/API/V1/SDMX/V21/datasource/tradestats-tariff/"
        f"reporter/{importer.lower()}/year/{year}/partner/{partner_part}/"
        f"product/{product}/indicator/{indicator}"
    )
# -------------------------------
# Tidy conversion helpers
# -------------------------------

def tidy_trade_json(raw: dict, meta: Dict[str, object]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    data = raw if isinstance(raw, list) else raw.get("data") or raw.get("value") or raw.get("Data") or raw.get("series") or []
    for item in data:
        rows.append({
            "year": item.get("Year") or meta.get("year"),
            "flow": meta.get("flow"),
            "importer": item.get("Reporter") or meta.get("importer"),
            "partner": item.get("Partner") or meta.get("partner"),
            "hs_code": item.get("CommodityCode") or meta.get("hs_code"),
            "trade_value_usd": item.get("TradeValue") or item.get("Value") or item.get("TradeValueUSD"),
            "quantity": item.get("Qty"),
            "unit": item.get("QtyUnit"),
        })
    return rows

def tidy_tariff_json(raw: dict, meta: Dict[str, object]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    data = raw if isinstance(raw, list) else raw.get("data") or raw.get("value") or raw.get("Data") or raw.get("series") or []
    for item in data:
        rows.append({
            "year": item.get("Year") or meta.get("year"),
            "importer": item.get("Reporter") or meta.get("importer"),
            "partner": item.get("Partner") or meta.get("partner"),
            "hs_code": item.get("CommodityCode") or meta.get("hs_code"),
            "mfn_simple_avg": item.get("MFN_SimpleAverage") or item.get("MFNRate"),
            "pref_simple_avg": item.get("Pref_SimpleAverage") or item.get("PrefRate"),
            "num_lines": item.get("NumLines"),
            "min_tariff": item.get("MinTariff"),
            "max_tariff": item.get("MaxTariff"),
        })
    return rows



# -------------------------------
# Summarization utilities
# -------------------------------

def top_by_value(rows: List[Dict[str, object]], group_key: str, k: int = 10) -> List[Tuple[str, float]]:
    agg: Dict[str, float] = {}
    for r in rows:
        key = str(r.get(group_key) or "")
        val = r.get("trade_value_usd")
        try:
            v = float(val) if val is not None else 0.0
        except Exception:
            v = 0.0
        agg[key] = agg.get(key, 0.0) + v
    # sort descending
    return sorted(agg.items(), key=lambda x: x[1], reverse=True)[:k]

# -------------------------------
# Core fetchers
# -------------------------------

def fetch_trade(importer: str, partner: Optional[str], hs: Optional[HSProduct], years: List[int], flow: str, limit: int, indicator: str) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    all_rows: List[Dict[str, object]] = []
    meta = {"flow": flow, "importer": importer, "partner": partner or "ALL", "hs_code": hs.code if hs else "ALL"}
    ylist = years or []
    if not ylist:
        # If "latest" requested, define your logic here; for now pick current year - 1
        ylist = [datetime.now().year - 1]
    for y in ylist:
        url = build_trade_url(y, importer, partner or "WLD", hs, indicator)
        log(f"GET {url}")
        raw = http_get_json(url, params={"format": "JSON"})

        meta_with_year = dict(meta)
        meta_with_year["year"] = y
        rows = tidy_trade_json(raw, meta_with_year)
        all_rows.extend(rows)
        if len(all_rows) > limit:
            log(f"Reached limit {limit}; truncating results")
            all_rows = all_rows[:limit]
            break
    return all_rows, {"kind": "trade", **meta}


def fetch_tariffs(importer: str, partner: Optional[str], hs: Optional[HSProduct], years: List[int], limit: int, indicator: str) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    all_rows: List[Dict[str, object]] = []
    meta = {"importer": importer, "partner": partner or "ALL", "hs_code": hs.code if hs else "ALL"}
    ylist = years or [datetime.now().year - 1]
    for y in ylist:
        url = build_tariff_url(y, importer, partner, hs, indicator)
        log(f"GET {url}")
        raw = http_get_json(url, params={"format": "JSON"})

        meta_with_year = dict(meta)
        meta_with_year["year"] = y
        rows = tidy_tariff_json(raw, meta_with_year)
        all_rows.extend(rows)
        if len(all_rows) > limit:
            log(f"Reached limit {limit}; truncating results")
            all_rows = all_rows[:limit]
            break
    return all_rows, {"kind": "tariff", **meta}

# -------------------------------
# CLI
# -------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Query WITS trade and tariff data with caching")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--imports", action="store_true", help="Fetch imports")
    mode.add_argument("--exports", action="store_true", help="Fetch exports")
    mode.add_argument("--tariffs", action="store_true", help="Fetch tariff data")

    p.add_argument("--importer", type=str, help="Importer country (ISO3 or common name)")
    # Allow both --exporter and --partner as synonyms
    p.add_argument("--exporter", type=str, help="Partner country (ISO3 or name)")
    p.add_argument("--partner", type=str, help="Partner country (alias for --exporter)")
    p.add_argument("--product", type=str, help="HS code filter. Accepts HS_85, 85, 8501, 850110")

    p.add_argument("--indicator", type=str, default=None, help="Indicator code (e.g., MPRT-TRD-VL, XPRT-TRD-VL, AHS-SMPL-AVRG)")

    p.add_argument("--year", type=int, help="Single year")
    p.add_argument("--years", type=str, help="Comma-separated list of years")
    p.add_argument("--start", type=int, help="Start year for a range")
    p.add_argument("--end", type=int, help="End year for a range")
    p.add_argument("--latest", action="store_true", help="Use latest available year")

    p.add_argument("--format", choices=["csv", "json", "both"], default="both", help="Output format")
    p.add_argument("--outfile", type=str, help="Optional output file path prefix")
    p.add_argument("--nocache", action="store_true", help="Bypass cache and force refresh")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Record limit to prevent huge pulls")
    p.add_argument("--summarize", action="store_true", help="Print top 10 partners and products by value (trade only)")

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    # Determine mode
    mode = "trade"
    flow = "imports"
    if args.tariffs:
        mode = "tariff"
    elif args.exports:
        flow = "exports"
        mode = "trade"

    if not args.importer:
        print("--importer is required", file=sys.stderr)
        return 2

    # Normalize CLI arguments before using them
    importer = normalize_country(args.importer)
    partner_arg = args.partner or args.exporter
    partner = normalize_country(partner_arg) if partner_arg else None
    hs = normalize_product(args.product)
    ys = normalize_years(args.year, args.years, args.start, args.end, args.latest)

    # Choose a default indicator if not provided
    indicator = args.indicator

    if mode == "trade":
        if not indicator:
            indicator = "MPRT-TRD-VL" if flow == "imports" else "XPRT-TRD-VL"
    else:
        if not indicator:
            indicator = "AHS-SMPL-AVRG"

    # Compose key for caching
    keydict = {
        "mode": mode,
        "flow": flow if mode == "trade" else None,
        "importer": importer,
        "partner": partner or "ALL",
        "product": asdict(hs) if hs else None,
        "years": ys.years,
        "indicator": indicator,
    }

    json_path, csv_path = cache_paths(mode, keydict)

    rows: List[Dict[str, object]]
    meta: Dict[str, object]

    if not args.nocache and os.path.exists(json_path) and os.path.exists(csv_path):
        log(f"Using cache: {json_path}")
        raw = read_json(json_path)
        rows = raw.get("rows", [])
        meta = raw.get("meta", {})

    else:
        if mode == "trade":
            rows, meta = fetch_trade(importer, partner, hs, ys.years, flow, args.limit, indicator)
        else:
            rows, meta = fetch_tariffs(importer, partner, hs, ys.years, args.limit, indicator)

        write_json(json_path, {"meta": meta, "rows": rows})
        # Define tidy CSV columns
        if mode == "trade":
            cols = ["year", "flow", "importer", "partner", "hs_code", "trade_value_usd", "quantity", "unit"]
        else:
            cols = ["year", "importer", "partner", "hs_code", "mfn_simple_avg", "pref_simple_avg", "num_lines", "min_tariff", "max_tariff"]
        write_csv(csv_path, rows, cols)

    # Prepare output paths
    out_base = args.outfile or os.path.splitext(csv_path)[0]
    out_csv = out_base + ".csv"
    out_json = out_base + ".json"

    # Copy or reuse cached files according to requested format
    if args.format in ("csv", "both") and csv_path != out_csv:
        write_csv(out_csv, rows, [k for k in rows[0].keys()] if rows else [])
    if args.format in ("json", "both") and json_path != out_json:
        write_json(out_json, {"meta": meta, "rows": rows})

    # Optional summaries (trade only)
    if args.summarize and mode == "trade":
        if rows:
            top_partners = top_by_value(rows, "partner", 10)
            top_products = top_by_value(rows, "hs_code", 10)
            print("\nTop partners by trade value (USD):")
            for name, val in top_partners:
                print(f"  {name:>6}  {val:,.0f}")
            print("\nTop products (HS) by trade value (USD):")
            for code, val in top_products:
                print(f"  {code:>6}  {val:,.0f}")
        else:
            print("No rows to summarize.")

    # Print where files are
    if args.format in ("csv", "both"):
        print(f"CSV: {out_csv}")
    if args.format in ("json", "both"):
        print(f"JSON: {out_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
