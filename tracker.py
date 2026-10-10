"""
tracker.py  -  SDG 2030 Progress Tracker
Downloads real indicator data from the World Bank Open Data API, fits a trend
to each one, and reports whether a country is on track to meet its SDG target.
Results are also saved to SQLite (results.db) and CSV so you can query them.

Examples:
    python tracker.py                    # Nigeria (default)
    python tracker.py KEN GHA ZAF        # several countries (ISO3 codes)
    python tracker.py --offline          # no internet: uses made-up DEMO data
    python tracker.py NGA --chart        # also save a chart (needs: pip install matplotlib)
"""

import argparse                         # reads command-line options like --offline
import csv                              # writes the results CSV
import json                             # turns the API's JSON text into Python lists/dicts
import sqlite3                          # stores results in a database
import urllib.request                   # downloads from the internet (built in, no pip needed)
from pathlib import Path                # file paths

from trend import assess                # our own maths module (trend.py)

ROOT = Path(__file__).parent            # this project's folder
CACHE_DIR = ROOT / "data"               # downloaded API responses are cached here
API = "https://api.worldbank.org/v2/country/{country}/indicator/{code}?format=json&per_page=100&date=2000:2025"

# The indicators we track. Each maps a World Bank code to the SDG target it measures.
#   target           = the value that counts as "achieved"
#   higher_is_better = True if we want the number to go up
#   is_percent       = True if the value is a 0-100 percentage
INDICATORS = {
    "SI.POV.DDAY":    {"sdg": "1.1", "name": "Extreme poverty (% of population)",
                       "target": 3.0,  "higher_is_better": False, "is_percent": True},
    "SN.ITK.DEFC.ZS": {"sdg": "2.1", "name": "Undernourishment (% of population)",
                       "target": 2.5,  "higher_is_better": False, "is_percent": True},
    "SH.DYN.MORT":    {"sdg": "3.2", "name": "Under-5 deaths per 1,000 births",
                       "target": 25.0, "higher_is_better": False, "is_percent": False},
    "SE.PRM.CMPT.ZS": {"sdg": "4.1", "name": "Primary completion rate (%)",
                       "target": 100.0, "higher_is_better": True, "is_percent": True},
    "SH.H2O.BASW.ZS": {"sdg": "6.1", "name": "Basic drinking water access (%)",
                       "target": 100.0, "higher_is_better": True, "is_percent": True},
    "EG.ELC.ACCS.ZS": {"sdg": "7.1", "name": "Access to electricity (%)",
                       "target": 100.0, "higher_is_better": True, "is_percent": True},
}


def fetch_series(country, code):
    """
    Return {year: value} for one country + indicator, using a local cache so we
    don't download the same thing twice.
    """
    CACHE_DIR.mkdir(exist_ok=True)                          # make data/ if needed
    cache_file = CACHE_DIR / f"{country}_{code}.json"       # e.g. data/NGA_EG.ELC.ACCS.ZS.json
    if cache_file.exists():                                 # already downloaded before?
        payload = json.loads(cache_file.read_text(encoding="utf-8"))  # read it from disk
    else:
        url = API.format(country=country, code=code)        # fill {country} and {code} into the URL
        with urllib.request.urlopen(url, timeout=30) as resp:   # send the HTTP request (30s limit)
            payload = json.loads(resp.read().decode("utf-8"))   # bytes -> text -> Python objects
        cache_file.write_text(json.dumps(payload), encoding="utf-8")  # save for next time

    # The API returns [metadata, rows]. If something went wrong there is no second item.
    if len(payload) < 2 or payload[1] is None:
        return {}                                           # no data for this country/indicator
    return {int(row["date"]): row["value"]                  # "2022" -> 2022
            for row in payload[1]
            if row["value"] is not None}                    # skip years the country didn't report


def demo_series(code):
    """
    MADE-UP data for offline practice. Not real statistics - do not quote these numbers.
    Produces a simple noisy trend so the rest of the program has something to work with.
    """
    start = {"SI.POV.DDAY": 45, "SN.ITK.DEFC.ZS": 12, "SH.DYN.MORT": 180,
             "SE.PRM.CMPT.ZS": 65, "SH.H2O.BASW.ZS": 55, "EG.ELC.ACCS.ZS": 45}[code]  # pick this indicator's start value
    step = {"SI.POV.DDAY": -0.8, "SN.ITK.DEFC.ZS": -0.1, "SH.DYN.MORT": -5,
            "SE.PRM.CMPT.ZS": 0.9, "SH.H2O.BASW.ZS": 1.6, "EG.ELC.ACCS.ZS": 1.2}[code]   # change per year
    wobble = [0.0, 0.6, -0.4, 0.3, -0.7, 0.5]                      # small fixed "noise" pattern
    return {2010 + i: start + step * i + wobble[i % len(wobble)]   # i % 6 cycles through the wobble list
            for i in range(14)}                                    # years 2010..2023


def analyse_country(country, offline):
    """Run assess() on every indicator for one country and return a list of result rows."""
    rows = []
    for code, meta in INDICATORS.items():                       # loop over code + its settings
        try:
            series = demo_series(code) if offline else fetch_series(country, code)
        except OSError as err:                                  # network errors are OSError subclasses
            print(f"  ! could not download {code} for {country}: {err}")
            continue                                            # skip this indicator, keep going
        recent = sorted(series.items())[-10:]                   # last 10 reported years, oldest first
        if len(recent) < 2:                                     # too little data for a trend
            print(f"  - {country} {code}: not enough data, skipped")
            continue
        years = [y for y, _ in recent]                          # split pairs into two lists
        values = [v for _, v in recent]
        result = assess(years, values, meta["target"], meta["higher_is_better"],
                        is_percent=meta["is_percent"])          # the maths lives in trend.py
        rows.append({"country": country, "sdg": meta["sdg"], "indicator": meta["name"],
                     "code": code, **result})                   # ** merges the result dict into this one
    return rows


def print_report(rows):
    """Print a readable table of results."""
    print(f"\n{'Country':<8}{'SDG':<6}{'Indicator':<38}{'Latest':>10}{'/yr':>9}{'2030':>9}{'Target':>8}  Status")
    print("-" * 100)
    for r in rows:
        status = "ON TRACK" if r["on_track"] else "OFF TRACK"
        eta = "" if r["on_track"] else (                         # extra hint for off-track goals
            "  (moving away)" if r["years_to_target"] is None
            else f"  (~{r['years_to_target']:.0f} yrs from {r['latest_year']})")
        print(f"{r['country']:<8}{r['sdg']:<6}{r['indicator']:<38}"   # :<38 = left-align in 38 chars
              f"{r['latest_value']:>10}{r['change_per_year']:>9}"     # :>10 = right-align in 10 chars
              f"{r['projected_2030']:>9}{r['target']:>8}  {status}{eta}")


def save_results(rows):
    """Save results to results.csv and results.db (table: progress)."""
    if not rows:
        return
    with open(ROOT / "results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())    # DictWriter writes dicts as rows
        writer.writeheader()
        writer.writerows(rows)

    with sqlite3.connect(ROOT / "results.db") as conn:
        conn.execute("DROP TABLE IF EXISTS progress")            # start fresh each run
        conn.execute("""
            CREATE TABLE progress (
                country TEXT, sdg TEXT, indicator TEXT, code TEXT,
                latest_year INTEGER, latest_value REAL, change_per_year REAL,
                projected_2030 REAL, target REAL, on_track INTEGER, years_to_target REAL
            )""")
        conn.executemany(                                         # named placeholders (:country) match dict keys
            """INSERT INTO progress VALUES (:country, :sdg, :indicator, :code, :latest_year,
               :latest_value, :change_per_year, :projected_2030, :target, :on_track, :years_to_target)""",
            rows)
        # A small SQL summary: how many goals each country is on track for.
        print("\nSummary (from SQL):")
        for country, on, total in conn.execute(
                "SELECT country, SUM(on_track), COUNT(*) FROM progress GROUP BY country ORDER BY 2 DESC"):
            print(f"  {country}: on track for {on} of {total} indicators")
    print("Saved results.csv and results.db")


def save_chart(country, offline):
    """Optional: plot each indicator's history for one country (needs matplotlib)."""
    try:
        import matplotlib.pyplot as plt                           # imported here so it's optional
    except ImportError:
        print("Chart skipped - install it with: pip install matplotlib")
        return
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))               # 2 rows x 3 columns of small charts
    for ax, (code, meta) in zip(axes.flat, INDICATORS.items()):   # .flat walks the grid one chart at a time
        series = demo_series(code) if offline else fetch_series(country, code)
        if series:
            years, values = zip(*sorted(series.items()))          # unzip [(y, v), ...] into two tuples
            ax.plot(years, values, marker="o")                    # the actual data
        ax.axhline(meta["target"], linestyle="--", color="grey")  # dashed line = the SDG target
        ax.set_title(f"SDG {meta['sdg']}: {meta['name']}", fontsize=9)
    fig.suptitle(f"{country} - progress toward 2030 targets" + (" (DEMO DATA)" if offline else ""))
    fig.tight_layout()                                            # stop titles overlapping
    out = ROOT / f"chart_{country}.png"
    fig.savefig(out, dpi=120)
    print(f"Saved {out.name}")


def main():
    parser = argparse.ArgumentParser(description="Check SDG 2030 progress with World Bank data.")
    parser.add_argument("countries", nargs="*", default=["NGA"],  # nargs="*" = zero or more values
                        help="ISO3 country codes, e.g. NGA KEN GHA")
    parser.add_argument("--offline", action="store_true", help="use made-up demo data (no internet)")
    parser.add_argument("--chart", action="store_true", help="save a PNG chart per country")
    args = parser.parse_args()                                    # read what the user typed

    countries = ["DEMO"] if args.offline else [c.upper() for c in args.countries]
    all_rows = []
    for country in countries:
        print(f"Analysing {country} ...")
        all_rows += analyse_country(country, args.offline)        # += adds the new rows to the list
        if args.chart:
            save_chart(country, args.offline)

    print_report(all_rows)
    save_results(all_rows)
    if args.offline:
        print("\nNOTE: --offline uses invented numbers. Run without it for real World Bank data.")


if __name__ == "__main__":
    main()
