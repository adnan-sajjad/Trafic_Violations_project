# Gurgaon Traffic Violation Analysis

Analysis of 1,000 simulated traffic violation records from Gurugram, covering
fine collection, violation patterns, location hotspots, and payment behavior.
Built with SQL (MySQL), Python (pandas/matplotlib), and Power BI.

## Project structure

```
.
├── data/
│   └── raw/
│       └── Gurgaon_Traffic_violation_data.csv   # source data (1,000 rows)
├── sql/
│   └── traffic_viol.sql                         # cleaning + KPI queries (MySQL)
├── python/
│   └── traffic_violation_analysis.py            # cleaning + KPIs + charts
├── dashboard/
│   └── gurguon_traffic_violation_dashboard.pbix  # Power BI dashboard
├── outputs/
│   └── charts/                                   # generated on script run
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python python/traffic_violation_analysis.py
```

Output: a cleaned CSV in `data/`, KPI printout in the terminal, and 7 chart
PNGs in `outputs/charts/`.

## What the analysis covers

- **KPIs**: total fine collected, total violations, average fine, repeat
  offender rate
- **Breakdowns**: by violation type, location, vehicle type, time of day,
  weather condition, payment status
- **Trend**: monthly violation volume
- **Ranking**: top 5 locations by revenue, revenue contribution % by
  violation type

## Data quality notes

The SQL script's null-check (`WHERE Fine_Amount IS NULL`) assumes zero
missing values. That assumption doesn't hold for this file — **50 of 1,000
rows (5%) have a missing `Fine_Amount`**. If you run the SQL script as-is
against the raw CSV, those 50 rows silently distort every SUM/AVG downstream
(MySQL excludes NULLs from aggregates, so revenue and average-fine totals
are undercounted, not just "off by a bit").

The Python script handles this explicitly: missing `Fine_Amount` values are
imputed with the median fine for that `Violation_Type`, and the count of
rows affected is logged when you run it. If you're presenting this project,
say so — an interviewer who spots 50 silently-dropped or NULL-propagated
rows in the SQL version and sees no mention of it in the writeup will read
it as either a miss or an omission.

Deduplication (on `Date + Location + Vehicle_Type + Violation_Type`) removes
3 duplicate rows — same logic in both SQL and Python.

## Notes on the SQL script

- `CREATE TABLE traffic_violation AS SELECT ... WHERE rn=1` replaces the
  table in place, which works but means the dedup step is destructive and
  not easily re-run — worth switching to a staging table if this goes into
  a portfolio writeup.
- Column renames reference `Fine_Amount (â‚¹)` — the mangled ₹ symbol means
  the source file was saved without UTF-8 encoding at some point. Not a bug
  in your SQL, but worth fixing at the CSV-export stage so it doesn't
  recur.
