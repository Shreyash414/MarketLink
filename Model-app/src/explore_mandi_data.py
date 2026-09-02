import pandas as pd

# -----------------------------------------
# 1. Load raw dataset
# -----------------------------------------

file_path = "data/raw/mandi_current_raw.csv"

df = pd.read_csv(file_path)

print("=" * 60)
print("DATASET BASIC INFORMATION")
print("=" * 60)

print("Rows:", df.shape[0])
print("Columns:", df.shape[1])


# -----------------------------------------
# 2. Column names
# -----------------------------------------

print("\n" + "=" * 60)
print("COLUMN NAMES")
print("=" * 60)

for column in df.columns:
    print(column)


# -----------------------------------------
# 3. First 5 records
# -----------------------------------------

print("\n" + "=" * 60)
print("FIRST 5 RECORDS")
print("=" * 60)

print(df.head())


# -----------------------------------------
# 4. Data types
# -----------------------------------------

print("\n" + "=" * 60)
print("DATA TYPES")
print("=" * 60)

print(df.dtypes)


# -----------------------------------------
# 5. Missing values
# -----------------------------------------

print("\n" + "=" * 60)
print("MISSING VALUES")
print("=" * 60)

print(df.isnull().sum())


# -----------------------------------------
# 6. Duplicate rows
# -----------------------------------------

print("\n" + "=" * 60)
print("DUPLICATES")
print("=" * 60)

print("Duplicate rows:", df.duplicated().sum())


# -----------------------------------------
# 7. Date information
# -----------------------------------------

print("\n" + "=" * 60)
print("DATE INFORMATION")
print("=" * 60)

df["arrival_date"] = pd.to_datetime(
    df["arrival_date"],
    dayfirst=True,
    errors="coerce"
)

print("Earliest date:", df["arrival_date"].min())
print("Latest date:", df["arrival_date"].max())

print("\nNumber of unique dates:")
print(df["arrival_date"].nunique())


# -----------------------------------------
# 8. States
# -----------------------------------------

print("\n" + "=" * 60)
print("STATE INFORMATION")
print("=" * 60)

print("Number of states:", df["state"].nunique())

print("\nTop 20 states:")

print(
    df["state"]
    .value_counts()
    .head(20)
)


# -----------------------------------------
# 9. Markets
# -----------------------------------------

print("\n" + "=" * 60)
print("MARKET INFORMATION")
print("=" * 60)

print("Number of markets:", df["market"].nunique())

print("\nTop 20 markets:")

print(
    df["market"]
    .value_counts()
    .head(20)
)


# -----------------------------------------
# 10. Commodities
# -----------------------------------------

print("\n" + "=" * 60)
print("COMMODITY INFORMATION")
print("=" * 60)

print("Number of commodities:", df["commodity"].nunique())

print("\nTop 30 commodities:")

print(
    df["commodity"]
    .value_counts()
    .head(30)
)


# -----------------------------------------
# 11. Price information
# -----------------------------------------

print("\n" + "=" * 60)
print("PRICE INFORMATION")
print("=" * 60)

price_columns = [
    "min_price",
    "max_price",
    "modal_price"
]

print(
    df[price_columns].describe()
)


# -----------------------------------------
# 12. Invalid prices
# -----------------------------------------

print("\n" + "=" * 60)
print("INVALID PRICE CHECK")
print("=" * 60)

for column in price_columns:

    print(
        column,
        "zero values:",
        (df[column] == 0).sum()
    )

    print(
        column,
        "negative values:",
        (df[column] < 0).sum()
    )


# -----------------------------------------
# 13. Final
# -----------------------------------------

print("\n" + "=" * 60)
print("EXPLORATION COMPLETE")
print("=" * 60)