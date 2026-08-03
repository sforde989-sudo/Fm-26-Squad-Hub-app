# FM26 Squad Hub

A Streamlit dashboard for Football Manager 2026 that turns your in-game data exports into a full squad-management and scouting cockpit — squad health, tactical fit, transfer decisions, and recruitment, all in one place.

## What it does

Upload your FM26 squad CSV export and the app builds ten linked views:

| Tab | What it's for |
|---|---|
| 📋 **Squad Sheet** | Full squad table — sortable, filterable, exportable. |
| 📈 **Analytics** | Configurable scatter plots and bar charts across any two stats, filterable by Best Position. |
| 🎯 **Radar & Compare** | Compare 2–4 players on a radar, raw-stats table, bar chart, and percentile pizza chart. Metrics auto-preset from the first player's position and fully editable. |
| ⏳ **Squad Planning** | Composite Squad Score per player (benchmark fit, role fit, age curve, form, minutes) with a plain-language Keep/Rotate/Develop/Loan/Release/Sell verdict and detailed reasoning for each. |
| 🔀 **Transfers** | Log and track transfer activity. |
| 📖 **Club Chronicle** | Season archive and career records. |
| 🕵️ **Scouting** | Upload an external player database (e.g. a rival league or a target club export) and score every candidate 0–100 against FM's Good/OK/Poor benchmark tables for their role — plus a Scatter Explorer for FM-style stat-vs-stat plots, and support for adding your own custom scoring metrics with auto-suggested thresholds. |
| 📄 **Player Report** | Individual PDF-style scouting report per player. |
| 🏆 **Elite Benchmark** | Upload a title-winning squad's export (Bayern, Real Madrid, etc.) and compare your players — or your whole squad by position — against that standard, with a gap percentage and priority-recruitment flags. |
| 🔄 **Replace/Upgrade** | Pick a player who's leaving and get a ranked list of replacements from your scouting database, matched to their exact role metrics, with the single best contributor called out per metric and a minutes-adjusted reliability score so small-sample stats don't skew the ranking. |

## Setup

1. Install dependencies: `conda activate fm26hub` (or your own venv) then `pip install streamlit pandas plotly numpy`
2. Run: `streamlit run FM26_Squad_Hub_app.py`, or double-click `Launch FM26 Hub.bat` on Windows

## Data you'll need

- **Squad export** (required) — CSV/XLSX export of your current squad from FM26, with per-90 stats columns
- **Scouting database export** (optional) — same format, from any pool of external players, used by the Scouting and Replace/Upgrade tabs
- **Reference squad export** (optional) — same format, from a target/elite club, used by Elite Benchmark
- **Club badge pack** (optional, cosmetic) — place crest PNGs at `badges/top-5-football-leagues/<league>/<club>.png` next to the script to show club badges in the header and sidebar; the app has color themes pre-loaded for all clubs across the top 5 European leagues regardless of whether badge images are present

## Sharing with others

Since the app reads local FM export files rather than a live game connection, each tester should run it locally against their own save export rather than connecting to your machine. See in-app guidance or ask for a walkthrough of Streamlit Community Cloud vs. local packaging.

## Notes

- All scoring and benchmark logic is transparent and editable in the source — thresholds live in the `FM_BENCHMARKS` and `ROLE_WEIGHTS` dictionaries near the top of the file.
- Built for iterative use across a save — most tabs work incrementally as your export data updates week to week.
