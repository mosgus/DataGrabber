# WHO.py (minimal working example for obesity in WHO Europe)
import os, csv, sys, json, time
import requests

WHO_GHO_BASE = "https://ghoapi.azureedge.net/api"
OUT_DIR = os.path.join("data", "who")
USER_AGENT = "WHO-CLI/0.1"

OBESITY_TABLES = {
    "age_std": "NCD_BMI_30A",
    "crude":   "NCD_BMI_30C",
}
# WHO European Region members (ISO3). Source: WHO list of countries by region.
WHO_EURO_ISO3 = [
    "ALB","AND","ARM","AUT","AZE","BLR","BEL","BIH","BGR","HRV","CYP","CZE","DNK",
    "EST","FIN","FRA","GEO","DEU","GRC","HUN","ISL","IRL","ISR","ITA","KAZ","KGZ",
    "LVA","LTU","LUX","MLT","MCO","MNE","NLD","MKD","NOR","POL","PRT","MDA","ROU",
    "RUS","SMR","SRB","SVK","SVN","ESP","SWE","CHE","TJK","TUR","TKM","UKR","GBR",
    "UZB"
]

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def make_session():
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    s.headers.update({"User-Agent": USER_AGENT})
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

SESSION = make_session()

def load_existing_keys(csv_path: str) -> set[tuple[str, int]]:
    keys: set[tuple[str, int]] = set()
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return keys
    with open(csv_path, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            try:
                iso = (row.get("iso3") or "").strip().upper()
                yr = int(row.get("year")) if row.get("year") else None
                if iso and yr:
                    keys.add((iso, yr))
            except Exception:
                continue
    return keys


def append_rows_unique(csv_path: str, rows: list[dict], fieldnames: list[str]) -> int:
    """
    Appends only rows whose (iso3, year) are not present.
    Creates the file with header if it doesn't exist.
    Returns number of rows appended.
    """
    existing = load_existing_keys(csv_path)
    new_rows = []
    for r in rows:
        iso = (r.get("iso3") or "").upper()
        yr = int(r.get("year")) if r.get("year") is not None else None
        if iso and yr and (iso, yr) not in existing:
            new_rows.append(r)

    # Create file with header if missing
    new_file = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if new_file:
            w.writeheader()
        for r in new_rows:
            w.writerow({k: r.get(k) for k in fieldnames})

    return len(new_rows)

def fetch_obesity_europe_bulk(year: int) -> list[dict]:
    """
    Fetch ALL WHO-Europe rows for the given year, following OData pagination.
    Only keeps both-sex records.
    """
    table = OBESITY_TABLES.get(os.getenv("WHO_OBESITY_VARIANT", "age_std"), "NCD_BMI_30A")
    base_url = f"{WHO_GHO_BASE}/{table}"
    params = {
        "$filter": f"TimeDim eq {int(year)}",
        "$select": "SpatialDim,TimeDim,NumericValue,Value,Dim1",
        "$format": "JSON",
    }

    def is_both(rec):
        return rec.get("Dim1") in (None, "", "BTSX", "BTH", "BTSX_BTH")

    out: list[dict] = []
    next_url, next_params = base_url, params

    for _ in range(200):  # safety cap
        r = SESSION.get(next_url, params=next_params, timeout=60)
        if r.status_code not in (200, 204):
            break
        payload = r.json()
        vals = payload.get("value", []) or []
        for rec in vals:
            iso3 = rec.get("SpatialDim")
            if iso3 in WHO_EURO_ISO3 and is_both(rec):
                out.append({
                    "iso3": iso3,
                    "year": rec.get("TimeDim"),
                    "value_percent": rec.get("NumericValue", rec.get("Value")),
                    "sex": rec.get("Dim1") or "BOTH",
                })
        next_link = payload.get("@odata.nextLink")
        if not next_link:
            break
        # nextLink is absolute; pass it directly, drop params
        next_url, next_params = next_link, None

    return out

def fetch_obesity_europe_all() -> list[dict]:
    """
    Pull ALL years for WHO European Region from the obesity (age-standardized) table,
    then filter locally to Europe and both sexes. Handles OData pagination.
    """
    table = "NCD_BMI_30A"  # use NCD_BMI_30C for crude
    url = f"{WHO_GHO_BASE}/{table}"
    params = {"$select": "SpatialDim,TimeDim,NumericValue,Value,Dim1", "$format": "JSON"}

    def is_both(rec):
        return rec.get("Dim1") in (None, "", "BTSX", "BTH", "BTSX_BTH")

    out: list[dict] = []

    # Follow @odata.nextLink if present
    next_url, next_params = url, params
    for _ in range(100):  # hard cap to avoid runaway loops
        r = SESSION.get(next_url, params=next_params, timeout=60)
        if r.status_code not in (200, 204):
            break
        payload = r.json()
        vals = payload.get("value", []) or []
        for rec in vals:
            iso3 = rec.get("SpatialDim")
            if iso3 in WHO_EURO_ISO3 and is_both(rec):
                out.append({
                    "iso3": iso3,
                    "year": rec.get("TimeDim"),
                    "value_percent": rec.get("NumericValue", rec.get("Value")),
                    "sex": rec.get("Dim1") or "BOTH",
                })
        next_link = payload.get("@odata.nextLink")
        if not next_link:
            break
        # When nextLink is an absolute URL, pass it directly and drop params
        next_url, next_params = next_link, None

    return out

def fetch_obesity_country_year(iso3: str, year: int) -> dict | None:
    """
    Try filtered query first. If WHO returns 404 (common quirk), fetch unfiltered data
    for this indicator and filter in Python. Also falls back to latest <= requested year.
    """
    # Age-standardized adult obesity (use NCD_BMI_30C for crude)
    table = OBESITY_TABLES.get(os.getenv("WHO_OBESITY_VARIANT", "age_std"), "NCD_BMI_30A")
    url = f"{WHO_GHO_BASE}/{table}"

    headers = {"User-Agent": USER_AGENT}

    def pick_both_sexes(rec_list):
        for rec in rec_list:
            if rec.get("Dim1") in (None, "", "BTSX", "BTH", "BTSX_BTH"):
                return rec
        return rec_list[0] if rec_list else None

    # 1) Try exact year with $filter (fast path)
    params_exact = {"$filter": f"SpatialDim eq '{iso3}' and TimeDim eq {int(year)}"}
    r = SESSION.get(url, params=params_exact, headers=headers, timeout=30)
    if r.status_code in (429, 503):
        time.sleep(1)
        r = SESSION.get(url, params=params_exact, headers=headers, timeout=30)

    if r.status_code == 200:
        data = r.json().get("value", [])
        rec = pick_both_sexes(data)
        if rec:
            return {
                "iso3": rec.get("SpatialDim"),
                "year": rec.get("TimeDim"),
                "value_percent": rec.get("Value"),
                "sex": rec.get("Dim1") or "BOTH"
            }

    # 2) If filtered call fails or empty, fetch unfiltered indicator and filter client-side
    if r.status_code == 404 or r.status_code == 400:
        r_all = SESSION.get(url, headers=headers, timeout=30)
        if r_all.status_code == 404:
            # rare edge case: retry once after a brief wait
            time.sleep(0.5)
            r_all = SESSION.get(url, headers=headers, timeout=30)
        r_all.raise_for_status()
        all_rows = r_all.json().get("value", [])

        # exact year first
        exact = [d for d in all_rows if d.get("SpatialDim") == iso3 and d.get("TimeDim") == int(year)]
        rec = pick_both_sexes(exact)
        if rec:
            return {
                "iso3": rec.get("SpatialDim"),
                "year": rec.get("TimeDim"),
                "value_percent": rec.get("NumericValue", rec.get("Value")),
                "sex": rec.get("Dim1") or "BOTH"
            }

        # then latest year <= requested
        le = [d for d in all_rows if d.get("SpatialDim") == iso3 and isinstance(d.get("TimeDim"), int) and d["TimeDim"] <= int(year)]
        le.sort(key=lambda x: x.get("TimeDim", -1), reverse=True)
        rec2 = pick_both_sexes(le)
        if rec2:
            return {
                "iso3": rec2.get("SpatialDim"),
                "year": rec2.get("TimeDim"),
                "value_percent": rec2.get("Value"),
                "sex": rec2.get("Dim1") or "BOTH"
            }

    # 3) As a final fallback (filtered call was 200 but empty)
    params_fallback = {
        "$filter": f"SpatialDim eq '{iso3}' and TimeDim le {int(year)}",
        "$orderby": "TimeDim desc",
        "$top": 1
    }
    r2 = SESSION.get(url, params=params_fallback, headers=headers, timeout=30)
    if r2.status_code == 200:
        data2 = r2.json().get("value", [])
        rec2 = pick_both_sexes(data2)
        if rec2:
            return {
                "iso3": rec2.get("SpatialDim"),
                "year": rec2.get("TimeDim"),
                "value_percent": rec2.get("Value"),
                "sex": rec2.get("Dim1") or "BOTH"
            }

    return None

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "2022"
    all_years_mode = isinstance(arg, str) and arg.strip().lower() == "all"
    year = None if all_years_mode else int(arg)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"obesity_who_europe_{year}.csv")

    rows = fetch_obesity_europe_bulk(year)
    for r in rows:
        if r["year"] != year:
            print(f"Note: {r['iso3']} had no {year} value; used {r['year']} instead.")

    if not rows:
        print(f"Warning: zero rows for {year}. Either no data for this indicator/year or a connectivity issue.")

    # Write CSV
    FIELDNAMES = ["iso3", "year", "value_percent", "sex"]
    added = append_rows_unique(out_path, rows, FIELDNAMES)
    print(f"CSV: {out_path} (+{added} new rows, {len(rows) - added} already present)")

    print(f"Wrote {len(rows)} rows to {out_path}")

if __name__ == "__main__":
    main()