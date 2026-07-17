"""
Gurgaon Traffic Violation Analysis
===================================
Python equivalent of traffic_viol.sql — cleans the raw data, computes the
same KPIs and breakdowns as the SQL script, and saves chart images to
outputs/charts/.

Run from the project root:
    python python/traffic_violation_analysis.py
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "data", "raw", "Gurgaon_Traffic_violation_data.csv")
CLEAN_PATH = os.path.join(BASE_DIR, "data", "traffic_violation_clean.csv")
CHART_DIR = os.path.join(BASE_DIR, "outputs", "charts")
os.makedirs(CHART_DIR, exist_ok=True)

plt.rcParams["figure.dpi"] = 110


def load_and_clean(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Rename columns (mirrors the ALTER TABLE ... RENAME COLUMN step)
    df = df.rename(columns={
        "Fine_Amount (₹)": "Fine_Amount",
        "Speed_Recorded (km/h)": "Speed_Recorded_kmphr",
        "Insurance_Penalty (₹)": "Insurance_Penalty",
    })

    # Date formatting (DD-MM-YYYY -> datetime)
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")

    # NOTE: the SQL script only checks `WHERE Fine_Amount IS NULL` and
    # assumes zero hits. That assumption is wrong for this file — see
    # README "Data quality notes". 50 of 1000 rows (5%) have a missing
    # Fine_Amount. Median imputation grouped by Violation_Type is used
    # here instead of silently dropping or leaving NaN, since fine
    # amount is central to every downstream KPI.
    missing_before = df["Fine_Amount"].isna().sum()
    df["Fine_Amount"] = df.groupby("Violation_Type")["Fine_Amount"].transform(
        lambda s: s.fillna(s.median())
    )
    df["Fine_Amount"] = df["Fine_Amount"].round(0).astype(int)

    # Deduplicate on the same key the SQL uses:
    # Date, Location, Vehicle_Type, Violation_Type
    before = len(df)
    df = df.drop_duplicates(subset=["Date", "Location", "Vehicle_Type", "Violation_Type"])
    dupes_removed = before - len(df)

    # Time intelligence columns
    df["year_no"] = df["Date"].dt.year
    df["month_no"] = df["Date"].dt.month
    df["month_name"] = df["Date"].dt.month_name()
    df["quarter_no"] = df["Date"].dt.quarter

    print(f"[clean] rows in: {before} | Fine_Amount nulls imputed: {missing_before} "
          f"| duplicate rows removed: {dupes_removed} | rows out: {len(df)}")

    return df


# ------------------------------------------------------------------
# KPI functions — each mirrors one numbered block in traffic_viol.sql
# ------------------------------------------------------------------

def kpi_summary(df: pd.DataFrame) -> dict:
    total_fine = df["Fine_Amount"].sum()
    total_violations = len(df)
    avg_fine = df["Fine_Amount"].mean()
    repeat_pct = (df["Repeat_Offender"].astype(str).str.upper() == "TRUE").mean() * 100

    summary = {
        "Total_Fine_Collected": round(total_fine),
        "Total_Violations": total_violations,
        "Avg_Fine": round(avg_fine, 2),
        "Repeat_Offender_pct": round(repeat_pct, 2),
    }
    return summary


def by_violation_type(df: pd.DataFrame) -> pd.DataFrame:
    out = (df.groupby("Violation_Type")
             .agg(Violations=("Violation_Type", "count"),
                  Revenue=("Fine_Amount", "sum"))
             .sort_values("Violations", ascending=False))
    return out


def by_location(df: pd.DataFrame) -> pd.DataFrame:
    out = (df.groupby("Location")
             .agg(Violations=("Location", "count"),
                  Total_Fine=("Fine_Amount", "sum"))
             .sort_values("Violations", ascending=False))
    return out


def by_vehicle_type(df: pd.DataFrame) -> pd.DataFrame:
    out = (df.groupby("Vehicle_Type")
             .agg(Violations=("Vehicle_Type", "count"),
                  Total_Fine=("Fine_Amount", "sum"))
             .sort_values("Violations", ascending=False))
    return out


def by_time_of_day(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("Time_of_Day")
              .agg(Violations=("Time_of_Day", "count"),
                   Total_Fine=("Fine_Amount", "sum")))


def by_weather(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("Weather_Condition")
              .agg(Violations=("Weather_Condition", "count"),
                   Total_Fine=("Fine_Amount", "sum"))
              .sort_values("Total_Fine", ascending=False))


def by_payment_status(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("Fine_Payment_Status")
              .agg(Total_Cases=("Fine_Payment_Status", "count"),
                   Total_Fine=("Fine_Amount", "sum")))


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    out = (df.groupby(df["Date"].dt.to_period("M"))
             .agg(Violations=("Date", "count"), Total_Fine=("Fine_Amount", "sum")))
    out.index = out.index.astype(str)
    return out


def top5_locations_by_revenue(df: pd.DataFrame) -> pd.DataFrame:
    rev = df.groupby("Location")["Fine_Amount"].sum().sort_values(ascending=False)
    return rev.head(5).to_frame("Revenue")


def violation_contribution_pct(df: pd.DataFrame) -> pd.DataFrame:
    rev = df.groupby("Violation_Type")["Fine_Amount"].sum().sort_values(ascending=False)
    pct = (rev / rev.sum() * 100).round(2)
    return pd.DataFrame({"Revenue": rev, "Contribution_pct": pct})


# ------------------------------------------------------------------
# Charts
# ------------------------------------------------------------------

def save_bar(series_or_df, value_col, title, filename, xlabel="", ylabel="", top_n=None):
    data = series_or_df
    if top_n:
        data = data.sort_values(value_col, ascending=False).head(top_n)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(data.index.astype(str), data[value_col], color="#2b6cb0")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename))
    plt.close(fig)


def save_line(df, value_col, title, filename, xlabel="", ylabel=""):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df.index.astype(str), df[value_col], marker="o", color="#2b6cb0")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename))
    plt.close(fig)


def save_pie(series, title, filename):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(series.values, labels=series.index, autopct="%1.1f%%", startangle=90)
    ax.set_title(title)
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename))
    plt.close(fig)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    df = load_and_clean(RAW_PATH)
    df.to_csv(CLEAN_PATH, index=False)
    print(f"[save] cleaned data written to {CLEAN_PATH}")

    print("\n=== KPI SUMMARY ===")
    for k, v in kpi_summary(df).items():
        print(f"{k}: {v}")

    violation_df = by_violation_type(df)
    location_df = by_location(df)
    vehicle_df = by_vehicle_type(df)
    tod_df = by_time_of_day(df)
    weather_df = by_weather(df)
    payment_df = by_payment_status(df)
    trend_df = monthly_trend(df)
    top5_df = top5_locations_by_revenue(df)
    contribution_df = violation_contribution_pct(df)

    print("\n=== TOP VIOLATION TYPES ===")
    print(violation_df)

    print("\n=== TOP 5 LOCATIONS BY REVENUE ===")
    print(top5_df)

    print("\n=== VIOLATION REVENUE CONTRIBUTION % ===")
    print(contribution_df)

    # Charts
    save_bar(violation_df, "Violations", "Violations by Type", "violations_by_type.png",
             ylabel="Count")
    save_bar(location_df, "Violations", "Top 10 Locations by Violations",
             "top_locations.png", ylabel="Count", top_n=10)
    save_bar(vehicle_df, "Violations", "Violations by Vehicle Type",
             "violations_by_vehicle.png", ylabel="Count")
    save_bar(tod_df, "Violations", "Violations by Time of Day",
             "violations_by_time_of_day.png", ylabel="Count")
    save_line(trend_df, "Violations", "Monthly Violation Trend",
              "monthly_trend.png", ylabel="Violations")
    save_pie(payment_df["Total_Cases"], "Fine Payment Status Split",
             "payment_status_split.png")
    save_pie(contribution_df["Revenue"], "Revenue Contribution by Violation Type",
             "revenue_contribution.png")

    print(f"\n[done] charts saved to {CHART_DIR}")


if __name__ == "__main__":
    main()
