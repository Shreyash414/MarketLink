import pandas as pd

# -----------------------------------------
# 1. Load cleaned dataset
# -----------------------------------------

file_path = "data/processed/onion_bhawanigarh_clean.csv"

df = pd.read_csv(file_path)

df["Arrival_Date"] = pd.to_datetime(
    df["Arrival_Date"],
    errors="coerce"
)

df = df.sort_values("Arrival_Date").reset_index(drop=True)


# -----------------------------------------
# 2. Create complete calendar
# -----------------------------------------

full_dates = pd.date_range(
    start=df["Arrival_Date"].min(),
    end=df["Arrival_Date"].max(),
    freq="D"
)


# -----------------------------------------
# 3. Find missing dates
# -----------------------------------------

existing_dates = set(df["Arrival_Date"])

missing_dates = [
    date
    for date in full_dates
    if date not in existing_dates
]


# -----------------------------------------
# 4. Basic results
# -----------------------------------------

print("=" * 60)
print("MISSING DATE ANALYSIS")
print("=" * 60)

print(
    "First date:",
    df["Arrival_Date"].min()
)

print(
    "Last date:",
    df["Arrival_Date"].max()
)

print(
    "Total calendar days:",
    len(full_dates)
)

print(
    "Observed market days:",
    len(existing_dates)
)

print(
    "Missing calendar days:",
    len(missing_dates)
)


# -----------------------------------------
# 5. Percentage
# -----------------------------------------

missing_percentage = (
    len(missing_dates)
    / len(full_dates)
) * 100

print(
    "Missing percentage:",
    round(missing_percentage, 2),
    "%"
)


# -----------------------------------------
# 6. Missing dates by year
# -----------------------------------------

missing_df = pd.DataFrame({
    "date": missing_dates
})

missing_df["year"] = (
    missing_df["date"].dt.year
)

print("\n" + "=" * 60)
print("MISSING DAYS BY YEAR")
print("=" * 60)

print(
    missing_df["year"]
    .value_counts()
    .sort_index()
)


# -----------------------------------------
# 7. Largest continuous missing periods
# -----------------------------------------

missing_df = missing_df.sort_values("date")

missing_df["gap"] = (
    missing_df["date"].diff().dt.days
)

group_id = (
    missing_df["gap"]
    .ne(1)
    .cumsum()
)

missing_periods = (
    missing_df
    .groupby(group_id)
    .agg(
        start=("date", "min"),
        end=("date", "max"),
        missing_days=("date", "count")
    )
    .sort_values(
        "missing_days",
        ascending=False
    )
)

print("\n" + "=" * 60)
print("LARGEST MISSING PERIODS")
print("=" * 60)

print(
    missing_periods.head(20).to_string(
        index=False
    )
)


# -----------------------------------------
# 8. Weekend analysis
# -----------------------------------------

df["day_of_week"] = (
    df["Arrival_Date"].dt.dayofweek
)

weekend_observations = df[
    df["day_of_week"].isin([5, 6])
]

print("\n" + "=" * 60)
print("WEEKEND INFORMATION")
print("=" * 60)

print(
    "Saturday/Sunday observations:",
    len(weekend_observations)
)


# -----------------------------------------
# 9. Final
# -----------------------------------------

print("\n" + "=" * 60)
print("MISSING DATE ANALYSIS COMPLETE")
print("=" * 60)