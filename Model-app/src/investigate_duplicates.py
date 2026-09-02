import pandas as pd

# -----------------------------------------
# 1. Load dataset
# -----------------------------------------

file_path = "data/raw/onion_bhawanigarh_history.csv"

df = pd.read_csv(file_path)

print("=" * 60)
print("DUPLICATE INVESTIGATION")
print("=" * 60)

print("Total rows:", len(df))


# -----------------------------------------
# 2. Count exact duplicates
# -----------------------------------------

exact_duplicates = df.duplicated(keep=False)

print("\nExact duplicate rows:")
print(exact_duplicates.sum())


# -----------------------------------------
# 3. Display duplicate rows
# -----------------------------------------

duplicates = df[exact_duplicates].sort_values(
    by=[
        "Arrival_Date",
        "Commodity",
        "Market"
    ]
)

print("\nFirst 20 duplicate rows:")

print(
    duplicates.head(20).to_string(index=False)
)


# -----------------------------------------
# 4. Check duplicate dates
# -----------------------------------------

print("\n" + "=" * 60)
print("DUPLICATE DATE CHECK")
print("=" * 60)

date_counts = (
    df.groupby("Arrival_Date")
      .size()
      .sort_values(ascending=False)
)

print("\nDates with multiple records:")

print(
    date_counts[
        date_counts > 1
    ].head(20)
)


# -----------------------------------------
# 5. Check duplicates based on
#    important market information
# -----------------------------------------

subset_columns = [
    "Arrival_Date",
    "Commodity",
    "State",
    "District",
    "Market",
    "Variety",
    "Grade"
]

subset_duplicates = df.duplicated(
    subset=subset_columns,
    keep=False
)

print("\nDuplicates based on:")
print(subset_columns)

print(
    "Count:",
    subset_duplicates.sum()
)


# -----------------------------------------
# 6. Check unique varieties
# -----------------------------------------

print("\n" + "=" * 60)
print("VARIETY INFORMATION")
print("=" * 60)

print(
    df["Variety"]
    .value_counts()
)


# -----------------------------------------
# 7. Check grades
# -----------------------------------------

print("\n" + "=" * 60)
print("GRADE INFORMATION")
print("=" * 60)

print(
    df["Grade"]
    .value_counts()
)


# -----------------------------------------
# 8. Check records per date
# -----------------------------------------

print("\n" + "=" * 60)
print("RECORDS PER DATE")
print("=" * 60)

print(
    date_counts.describe()
)


# -----------------------------------------
# 9. Final
# -----------------------------------------

print("\n" + "=" * 60)
print("DUPLICATE INVESTIGATION COMPLETE")
print("=" * 60)