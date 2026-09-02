import pandas as pd

# -----------------------------------------
# 1. Load RAW data
# -----------------------------------------

input_file = "data/raw/onion_bhawanigarh_history.csv"

df = pd.read_csv(input_file)

print("=" * 60)
print("BEFORE CLEANING")
print("=" * 60)

print("Rows:", len(df))


# -----------------------------------------
# 2. Convert date
# -----------------------------------------

df["Arrival_Date"] = pd.to_datetime(
    df["Arrival_Date"],
    errors="coerce"
)


# -----------------------------------------
# 3. Convert prices to numeric
# -----------------------------------------

price_columns = [
    "Min_Price",
    "Max_Price",
    "Modal_Price"
]

for column in price_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# -----------------------------------------
# 4. Check missing values
# -----------------------------------------

print("\nMissing values before cleaning:")

print(df.isnull().sum())


# -----------------------------------------
# 5. Remove exact duplicate rows
# -----------------------------------------

before = len(df)

df = df.drop_duplicates()

after = len(df)

removed = before - after

print("\nDuplicate removal:")
print("Before:", before)
print("After:", after)
print("Removed:", removed)


# -----------------------------------------
# 6. Remove invalid prices
# -----------------------------------------

before = len(df)

df = df[
    (df["Min_Price"] > 0) &
    (df["Max_Price"] > 0) &
    (df["Modal_Price"] > 0)
]

after = len(df)

print("\nInvalid price rows removed:", before - after)


# -----------------------------------------
# 7. Check logical price relationships
# -----------------------------------------

invalid_price_order = df[
    (df["Min_Price"] > df["Max_Price"]) |
    (df["Modal_Price"] < df["Min_Price"]) |
    (df["Modal_Price"] > df["Max_Price"])
]

print(
    "\nRows with logically invalid price relationships:",
    len(invalid_price_order)
)


# -----------------------------------------
# 8. Remove logically invalid rows
# -----------------------------------------

df = df[
    (df["Min_Price"] <= df["Max_Price"]) &
    (df["Modal_Price"] >= df["Min_Price"]) &
    (df["Modal_Price"] <= df["Max_Price"])
]


# -----------------------------------------
# 9. Sort by date
# -----------------------------------------

df = df.sort_values(
    "Arrival_Date"
).reset_index(drop=True)


# -----------------------------------------
# 10. Final information
# -----------------------------------------

print("\n" + "=" * 60)
print("AFTER CLEANING")
print("=" * 60)

print("Rows:", len(df))

print(
    "Earliest date:",
    df["Arrival_Date"].min()
)

print(
    "Latest date:",
    df["Arrival_Date"].max()
)

print(
    "Unique dates:",
    df["Arrival_Date"].nunique()
)

print(
    "Remaining duplicates:",
    df.duplicated().sum()
)


# -----------------------------------------
# 11. Save processed dataset
# -----------------------------------------

output_file = (
    "data/processed/"
    "onion_bhawanigarh_clean.csv"
)

df.to_csv(
    output_file,
    index=False
)

print("\nSaved successfully:")
print(output_file)