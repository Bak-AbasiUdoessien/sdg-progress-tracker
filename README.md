# SDG 2030 Progress Tracker

This Python command-line tool downloads **real** World Bank data for six SDG indicators. For each one it fits a trend line (least-squares, written by hand) and tells you if the country is **on track to hit the 2030 target**. If it isn't, it estimates how many years the target will actually take.

| SDG | Indicator (World Bank code) | Target used |
|---|---|---|
| 1.1 | Extreme poverty % (`SI.POV.DDAY`) | ≤ 3% |
| 2.1 | Undernourishment % (`SN.ITK.DEFC.ZS`) | ≤ 2.5% |
| 3.2 | Under-5 mortality per 1,000 (`SH.DYN.MORT`) | ≤ 25 |
| 4.1 | Primary completion % (`SE.PRM.CMPT.ZS`) | 100% |
| 6.1 | Basic drinking water % (`SH.H2O.BASW.ZS`) | 100% |
| 7.1 | Access to electricity % (`EG.ELC.ACCS.ZS`) | 100% |

## Run it (VS Code terminal)
```bash
python tracker.py                    # Nigeria (NGA) by default, real data
python tracker.py NGA KEN GHA ZAF    # compare countries (ISO3 codes)
python tracker.py --offline          # no internet: made-up DEMO data
pip install matplotlib               # optional, for charts
python tracker.py NGA --chart        # saves chart_NGA.png
python -m unittest discover tests    # run the unit tests
```
Results are saved to `results.csv` and to **`results.db`** (table `progress`). Try querying the database:
```sql
SELECT sdg, indicator, projected_2030, target FROM progress WHERE country = 'NGA' AND on_track = 0;
```

## How the logic works
1. **Fetch:** `urllib` calls `api.worldbank.org/v2/...`. Each response is cached in `data/`, so a re-run doesn't download it again.
2. **Clean:** years with no reported value are dropped, and only the last 10 reported years are kept.
3. **Model:** `trend.py` fits `value = slope × year + intercept` with the least-squares formula.
4. **Project:** the line is extended to 2030 and clamped to 0–100 for percentages.
5. **Judge:** the 2030 projection is compared with the target, taking into account whether a higher number is better or worse.
6. **ETA:** the program solves `target = slope × year + intercept` for the year the target would actually be reached.

## Limitations (good to mention in interviews)
- A straight line is a simplification, because progress usually slows down near 100%. A next step would be a logistic curve.
- The targets are simplified versions of the official UN targets.
- Some countries report certain indicators rarely, so their trends rest on few data points.
