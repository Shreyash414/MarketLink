import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

PROCESSED_DIR = "data/processed"
EDA_DIR = "data/processed/eda"

os.makedirs(EDA_DIR, exist_ok=True)


DATASETS = {
    "Bareilly": "onion_bareilly_model.csv",
    "Bargarh": "onion_bargarh_model.csv",
    "Nagpur": "onion_nagpur_model.csv"
}


# ============================================================
# LOAD DATA
# ============================================================

def load_market(market, filename):

    path = os.path.join(
        PROCESSED_DIR,
        filename
    )

    print("\n" + "=" * 80)
    print(f"LOADING {market}")
    print("=" * 80)

    df = pd.read_csv(path)

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    print("Rows:", len(df))
    print(
        "Date:",
        df["date"].min().date(),
        "→",
        df["date"].max().date()
    )

    return df


# ============================================================
# ADD TIME FEATURES
# ============================================================

def add_time_features(df):

    df = df.copy()

    df["year"] = df["date"].dt.year

    df["month"] = df["date"].dt.month

    df["month_name"] = df["date"].dt.month_name()

    df["day_of_week"] = df["date"].dt.dayofweek

    df["day_name"] = df["date"].dt.day_name()

    df["quarter"] = df["date"].dt.quarter

    return df


# ============================================================
# BASIC STATISTICS
# ============================================================

def basic_statistics(df, market):

    print("\n" + "-" * 80)
    print(f"BASIC STATISTICS — {market}")
    print("-" * 80)

    stats = df[
        [
            "min_price",
            "modal_price",
            "max_price"
        ]
    ].describe()

    print(
        stats.round(2).to_string()
    )

    stats.to_csv(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_basic_statistics.csv"
        )
    )

    return stats


# ============================================================
# YEARLY ANALYSIS
# ============================================================

def yearly_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"YEARLY ANALYSIS — {market}")
    print("-" * 80)

    yearly = (
        df.groupby("year")
        .agg(
            observations=("modal_price", "count"),
            mean_price=("modal_price", "mean"),
            median_price=("modal_price", "median"),
            min_price=("modal_price", "min"),
            max_price=("modal_price", "max"),
            std_price=("modal_price", "std")
        )
        .round(2)
    )

    print(
        yearly.to_string()
    )

    yearly.to_csv(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_yearly_analysis.csv"
        )
    )

    return yearly


# ============================================================
# MONTHLY SEASONALITY
# ============================================================

def monthly_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"MONTHLY SEASONALITY — {market}")
    print("-" * 80)

    monthly = (
        df.groupby("month")
        .agg(
            observations=("modal_price", "count"),
            mean_price=("modal_price", "mean"),
            median_price=("modal_price", "median"),
            min_price=("modal_price", "min"),
            max_price=("modal_price", "max"),
            std_price=("modal_price", "std")
        )
        .round(2)
    )

    print(
        monthly.to_string()
    )

    monthly.to_csv(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_monthly_analysis.csv"
        )
    )

    return monthly


# ============================================================
# MONTH + YEAR ANALYSIS
# ============================================================

def month_year_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"MONTH × YEAR ANALYSIS — {market}")
    print("-" * 80)

    result = (
        df.pivot_table(
            index="year",
            columns="month",
            values="modal_price",
            aggfunc="mean"
        )
        .round(2)
    )

    print(
        result.tail(10).to_string()
    )

    result.to_csv(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_month_year.csv"
        )
    )

    return result


# ============================================================
# PRICE CHANGE ANALYSIS
# ============================================================

def price_change_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"PRICE CHANGE ANALYSIS — {market}")
    print("-" * 80)

    df = df.copy()

    df["price_change"] = (
        df["modal_price"]
        .diff()
    )

    df["percentage_change"] = (
        df["modal_price"]
        .pct_change()
        * 100
    )

    print(
        "Average absolute price change:",
        round(
            df["price_change"]
            .abs()
            .mean(),
            2
        )
    )

    print(
        "Average percentage change:",
        round(
            df["percentage_change"]
            .abs()
            .mean(),
            2
        ),
        "%"
    )

    print(
        "Maximum increase:",
        round(
            df["percentage_change"]
            .max(),
            2
        ),
        "%"
    )

    print(
        "Maximum decrease:",
        round(
            df["percentage_change"]
            .min(),
            2
        ),
        "%"
    )

    df[
        [
            "date",
            "modal_price",
            "price_change",
            "percentage_change"
        ]
    ].to_csv(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_price_changes.csv"
        ),
        index=False
    )

    return df


# ============================================================
# ROLLING VOLATILITY
# ============================================================

def volatility_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"VOLATILITY ANALYSIS — {market}")
    print("-" * 80)

    df = df.copy()

    df["rolling_mean_30"] = (
        df["modal_price"]
        .rolling(30)
        .mean()
    )

    df["rolling_std_30"] = (
        df["modal_price"]
        .rolling(30)
        .std()
    )

    df["rolling_cv_30"] = (
        df["rolling_std_30"]
        /
        df["rolling_mean_30"]
    )

    print(
        "Average 30-observation rolling volatility:",
        round(
            df["rolling_std_30"]
            .mean(),
            2
        )
    )

    print(
        "Maximum 30-observation rolling volatility:",
        round(
            df["rolling_std_30"]
            .max(),
            2
        )
    )

    df[
        [
            "date",
            "modal_price",
            "rolling_mean_30",
            "rolling_std_30",
            "rolling_cv_30"
        ]
    ].to_csv(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_volatility.csv"
        ),
        index=False
    )

    return df


# ============================================================
# OUTLIER ANALYSIS
# ============================================================

def outlier_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"OUTLIER ANALYSIS — {market}")
    print("-" * 80)

    price = df["modal_price"]

    q1 = price.quantile(0.25)

    q3 = price.quantile(0.75)

    iqr = q3 - q1

    lower = q1 - 1.5 * iqr

    upper = q3 + 1.5 * iqr

    outliers = df[
        (df["modal_price"] < lower)
        |
        (df["modal_price"] > upper)
    ].copy()

    print(
        "Q1:",
        round(q1, 2)
    )

    print(
        "Q3:",
        round(q3, 2)
    )

    print(
        "IQR:",
        round(iqr, 2)
    )

    print(
        "Lower bound:",
        round(lower, 2)
    )

    print(
        "Upper bound:",
        round(upper, 2)
    )

    print(
        "Potential outliers:",
        len(outliers)
    )

    if len(outliers) > 0:

        print(
            "\nTop 10 highest potential outliers:"
        )

        print(
            outliers[
                [
                    "date",
                    "modal_price"
                ]
            ]
            .sort_values(
                "modal_price",
                ascending=False
            )
            .head(10)
            .to_string(index=False)
        )

    outliers.to_csv(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_outliers.csv"
        ),
        index=False
    )

    return outliers


# ============================================================
# RECENT TREND
# ============================================================

def recent_trend_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"RECENT TREND — {market}")
    print("-" * 80)

    latest_date = df["date"].max()

    # Last 3 years

    start_date = (
        latest_date
        - pd.DateOffset(years=3)
    )

    recent = df[
        df["date"] >= start_date
    ].copy()

    recent_yearly = (
        recent.groupby("year")
        ["modal_price"]
        .agg(
            [
                "count",
                "mean",
                "median",
                "min",
                "max"
            ]
        )
        .round(2)
    )

    print(
        "Last 3 years:"
    )

    print(
        recent_yearly.to_string()
    )

    recent.to_csv(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_recent_data.csv"
        ),
        index=False
    )

    return recent


# ============================================================
# MONTHLY SEASONAL INDEX
# ============================================================

def seasonal_index(df, market):

    print("\n" + "-" * 80)
    print(f"SEASONAL INDEX — {market}")
    print("-" * 80)

    overall_mean = (
        df["modal_price"]
        .mean()
    )

    monthly_mean = (
        df.groupby("month")
        ["modal_price"]
        .mean()
    )

    seasonal = pd.DataFrame()

    seasonal["monthly_mean"] = monthly_mean

    seasonal["seasonal_index"] = (
        monthly_mean /
        overall_mean
    )

    seasonal["seasonal_percentage"] = (
        seasonal["seasonal_index"]
        * 100
    )

    seasonal = seasonal.round(4)

    print(
        seasonal.to_string()
    )

    seasonal.to_csv(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_seasonal_index.csv"
        )
    )

    return seasonal


# ============================================================
# MARKET SUMMARY
# ============================================================

def create_market_summary(all_data):

    print("\n")
    print("=" * 80)
    print("MARKET COMPARISON")
    print("=" * 80)

    summary = []

    for market, df in all_data.items():

        summary.append(
            {
                "market": market,
                "observations": len(df),
                "start_date": df["date"].min().date(),
                "end_date": df["date"].max().date(),
                "mean_modal_price": round(
                    df["modal_price"].mean(),
                    2
                ),
                "median_modal_price": round(
                    df["modal_price"].median(),
                    2
                ),
                "std_modal_price": round(
                    df["modal_price"].std(),
                    2
                ),
                "min_modal_price": df[
                    "modal_price"
                ].min(),
                "max_modal_price": df[
                    "modal_price"
                ].max()
            }
        )

    summary_df = pd.DataFrame(
        summary
    )

    print(
        summary_df.to_string(
            index=False
        )
    )

    summary_df.to_csv(
        os.path.join(
            EDA_DIR,
            "market_comparison.csv"
        ),
        index=False
    )

    return summary_df


# ============================================================
# PLOT PRICE TREND
# ============================================================

def plot_price_trend(df, market):

    print(
        f"Creating price trend plot for {market}..."
    )

    plt.figure(
        figsize=(14, 6)
    )

    plt.plot(
        df["date"],
        df["modal_price"]
    )

    plt.title(
        f"{market} Onion Modal Price Trend"
    )

    plt.xlabel(
        "Date"
    )

    plt.ylabel(
        "Modal Price (₹/quintal)"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_price_trend.png"
        ),
        dpi=150
    )

    plt.close()


# ============================================================
# PLOT MONTHLY SEASONALITY
# ============================================================

def plot_monthly_seasonality(
    df,
    market
):

    monthly = (
        df.groupby("month")
        ["modal_price"]
        .mean()
    )

    plt.figure(
        figsize=(10, 6)
    )

    plt.plot(
        monthly.index,
        monthly.values,
        marker="o"
    )

    plt.title(
        f"{market} Monthly Onion Price Pattern"
    )

    plt.xlabel(
        "Month"
    )

    plt.ylabel(
        "Average Modal Price (₹/quintal)"
    )

    plt.xticks(
        range(1, 13)
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_monthly_seasonality.png"
        ),
        dpi=150
    )

    plt.close()


# ============================================================
# PLOT PRICE DISTRIBUTION
# ============================================================

def plot_distribution(df, market):

    plt.figure(
        figsize=(10, 6)
    )

    plt.hist(
        df["modal_price"],
        bins=50
    )

    plt.title(
        f"{market} Onion Modal Price Distribution"
    )

    plt.xlabel(
        "Modal Price (₹/quintal)"
    )

    plt.ylabel(
        "Frequency"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_price_distribution.png"
        ),
        dpi=150
    )

    plt.close()


# ============================================================
# PLOT YEARLY AVERAGE
# ============================================================

def plot_yearly_average(df, market):

    yearly = (
        df.groupby("year")
        ["modal_price"]
        .mean()
    )

    plt.figure(
        figsize=(12, 6)
    )

    plt.plot(
        yearly.index,
        yearly.values,
        marker="o"
    )

    plt.title(
        f"{market} Yearly Average Onion Price"
    )

    plt.xlabel(
        "Year"
    )

    plt.ylabel(
        "Average Modal Price (₹/quintal)"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            EDA_DIR,
            f"{market.lower()}_yearly_average.png"
        ),
        dpi=150
    )

    plt.close()


# ============================================================
# PROCESS MARKET
# ============================================================

def analyze_market(
    market,
    filename
):

    df = load_market(
        market,
        filename
    )

    df = add_time_features(
        df
    )

    basic_statistics(
        df,
        market
    )

    yearly_analysis(
        df,
        market
    )

    monthly_analysis(
        df,
        market
    )

    month_year_analysis(
        df,
        market
    )

    price_change_analysis(
        df,
        market
    )

    volatility_analysis(
        df,
        market
    )

    outlier_analysis(
        df,
        market
    )

    recent_trend_analysis(
        df,
        market
    )

    seasonal_index(
        df,
        market
    )

    plot_price_trend(
        df,
        market
    )

    plot_monthly_seasonality(
        df,
        market
    )

    plot_distribution(
        df,
        market
    )

    plot_yearly_average(
        df,
        market
    )

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 80)
    print("ONION MARKET EXPLORATORY DATA ANALYSIS")
    print("=" * 80)

    all_data = {}

    for market, filename in DATASETS.items():

        df = analyze_market(
            market,
            filename
        )

        all_data[market] = df

    create_market_summary(
        all_data
    )

    print("\n")
    print("=" * 80)
    print("EDA COMPLETE")
    print("=" * 80)

    print(
        "\nEDA files saved in:"
    )

    print(
        EDA_DIR
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()