import pandas as pd

# -----------------------------------------
# 1. Load cleaned dataset
# -----------------------------------------

file_path = "data/processed/onion_bhawanigarh_clean.csv"

df = pd.read_csv(file_path)

# Convert date
df["Arrival_Date"] = pd.to_datetime(
    df["Arrival_Date"],
    errors="coerce"
)

# Sort by date
df = df.sort_values("Arrival_Date").reset_index(drop=True)


# -----------------------------------------
# 2. Basic information
# -----------------------------------------

print("=" * 60)
print("TIME SERIES ANALYSIS")
print("=" * 60)

print("Total rows:", len(df))

print("Earliest date:", df["Arrival_Date"].min())

print("Latest date:", df["Arrival_Date"].max())

print("Unique dates:", df["Arrival_Date"].nunique())


# -----------------------------------------
# 3. Calculate gap between observations
# -----------------------------------------

df["date_gap"] = df["Arrival_Date"].diff().dt.days


# -----------------------------------------
# 4. Gap statistics
# -----------------------------------------

print("\n" + "=" * 60)
print("DATE GAP STATISTICS")
print("=" * 60)

print(
    df["date_gap"].describe()
)


# -----------------------------------------
# 5. Count gaps
# -----------------------------------------

print("\nNumber of gaps:")

print(
    "Same day (0 days):",
    (df["date_gap"] == 0).sum()
)

print(
    "1 day:",
    (df["date_gap"] == 1).sum()
)

print(
    "2–7 days:",
    ((df["date_gap"] >= 2) &
     (df["date_gap"] <= 7)).sum()
)

print(
    "8–30 days:",
    ((df["date_gap"] >= 8) &
     (df["date_gap"] <= 30)).sum()
)

print(
    "More than 30 days:",
    (df["date_gap"] > 30).sum()
)


# -----------------------------------------
# 6. Largest gaps
# -----------------------------------------

print("\n" + "=" * 60)
print("LARGEST GAPS")
print("=" * 60)

largest_gaps = (
    df[
        ["Arrival_Date", "date_gap"]
    ]
    .sort_values(
        "date_gap",
        ascending=False
    )
    .head(20)
)

print(largest_gaps.to_string(index=False))


# -----------------------------------------
# 7. Records per year
# -----------------------------------------

print("\n" + "=" * 60)
print("RECORDS PER YEAR")
print("=" * 60)

df["year"] = df["Arrival_Date"].dt.year

print(
    df["year"]
    .value_counts()
    .sort_index()
)


# -----------------------------------------
# 8. Records per month
# -----------------------------------------

print("\n" + "=" * 60)
print("RECORDS PER MONTH")
print("=" * 60)

df["month"] = df["Arrival_Date"].dt.month

print(
    df["month"]
    .value_counts()
    .sort_index()
)


# -----------------------------------------
# 9. Recent 5 years
# -----------------------------------------

print("\n" + "=" * 60)
print("RECENT YEARS")
print("=" * 60)

recent = (
    df.groupby("year")
      .size()
      .tail(5)
)

print(recent)


# -----------------------------------------
# 10. Final
# -----------------------------------------

print("\n" + "=" * 60)
print("TIME SERIES ANALYSIS COMPLETE")
print("=" * 60)