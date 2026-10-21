"""Data loading, caching, and filtering helpers for the OWID COVID-19 dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

DATA_PATH = "owid-covid-data.csv"
VACCINE_CFR_SUMMARY_PATH = "vaccination_cfr_summary.csv"
VACCINE_MANUFACTURER_PATH = "vaccinations-by-manufacturer.csv"

METRIC_GROUPS: dict[str, dict[str, str]] = {
    "Cases & deaths": {
        "total_cases": "Total cases",
        "new_cases": "New cases",
        "new_cases_smoothed": "New cases (7-day average)",
        "total_deaths": "Total deaths",
        "new_deaths": "New deaths",
        "new_deaths_smoothed": "New deaths (7-day average)",
        "total_cases_per_million": "Total cases per million",
        "new_cases_per_million": "New cases per million",
        "total_deaths_per_million": "Total deaths per million",
        "new_deaths_per_million": "New deaths per million",
        "reproduction_rate": "Reproduction rate",
    },
    "Testing": {
        "total_tests": "Total tests",
        "new_tests": "New tests",
        "total_tests_per_thousand": "Total tests per thousand",
        "new_tests_per_thousand": "New tests per thousand",
        "new_tests_smoothed": "New tests (7-day average)",
        "positive_rate": "Positive rate",
        "tests_per_case": "Tests per confirmed case",
    },
    "Vaccinations": {
        "total_vaccinations": "Total vaccine doses",
        "people_vaccinated": "People vaccinated (at least 1 dose)",
        "people_fully_vaccinated": "People fully vaccinated",
        "total_boosters": "Total booster doses",
        "new_vaccinations": "New doses administered",
        "total_vaccinations_per_hundred": "Doses per 100 people",
        "people_vaccinated_per_hundred": "People vaccinated per 100",
        "people_fully_vaccinated_per_hundred": "People fully vaccinated per 100",
        "total_boosters_per_hundred": "Booster doses per 100 people",
    },
    "Hospital & ICU": {
        "icu_patients": "ICU patients",
        "icu_patients_per_million": "ICU patients per million",
        "hosp_patients": "Hospital patients",
        "hosp_patients_per_million": "Hospital patients per million",
        "weekly_icu_admissions": "Weekly ICU admissions",
        "weekly_hosp_admissions": "Weekly hospital admissions",
    },
    "Policy & excess mortality": {
        "stringency_index": "Government stringency index",
        "excess_mortality": "Excess mortality (%)",
        "excess_mortality_cumulative": "Cumulative excess mortality (%)",
        "excess_mortality_cumulative_absolute": "Cumulative excess mortality (deaths)",
        "excess_mortality_cumulative_per_million": "Cumulative excess mortality per million",
    },
}

# Columns that are sparsely reported (most location-days have no value).
SPARSE_CATEGORIES = {"Hospital & ICU", "Policy & excess mortality"}

DEMOGRAPHIC_COLUMNS: dict[str, str] = {
    "population": "Population",
    "population_density": "Population density",
    "median_age": "Median age",
    "gdp_per_capita": "GDP per capita",
    "life_expectancy": "Life expectancy",
    "human_development_index": "Human Development Index",
    "hospital_beds_per_thousand": "Hospital beds per 1,000 people",
    "diabetes_prevalence": "Diabetes prevalence (%)",
}

# Key metrics shown side by side in the Compare tab, regardless of the
# sidebar's selected category/metric.
COMPARE_METRICS: dict[str, str] = {
    "total_cases_per_million": "Total cases / million",
    "total_deaths_per_million": "Total deaths / million",
    "people_fully_vaccinated_per_hundred": "Fully vaccinated / 100",
    "stringency_index": "Stringency index",
}


@st.cache_data(show_spinner="Loading OWID COVID-19 dataset...")
def load_data(path: str = DATA_PATH) -> pd.DataFrame:
    """Load the OWID dataset once per session and keep it cached in memory."""
    df = pd.read_csv(path, parse_dates=["date"])

    float_cols = df.select_dtypes(include="float64").columns
    df[float_cols] = df[float_cols].astype("float32")

    for col in ("iso_code", "continent", "location", "tests_units"):
        df[col] = df[col].astype("category")

    return df


def split_locations(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Split locations into real countries/regions (with a continent) vs. OWID
    aggregates (World, continents, EU, income groups), which have no continent.

    Note: some real regions (England, Scotland, Kosovo, Northern Cyprus, ...)
    use an "OWID_"-prefixed iso_code because they lack an official ISO 3166
    code, so iso_code alone cannot distinguish aggregates from real locations
    - continent is null only for the true aggregates.
    """
    is_aggregate = df["continent"].isna()

    countries = (
        df.loc[~is_aggregate, ["location", "continent"]]
        .drop_duplicates()
        .sort_values(["continent", "location"])
    )
    aggregates = sorted(df.loc[is_aggregate, "location"].unique().tolist())

    return countries, aggregates


def filter_data(
    df: pd.DataFrame,
    locations: list[str],
    start_date,
    end_date,
    columns: list[str],
) -> pd.DataFrame:
    """Filter the dataset to the selected locations, date range, and columns."""
    mask = (
        df["location"].isin(locations)
        & (df["date"] >= pd.Timestamp(start_date))
        & (df["date"] <= pd.Timestamp(end_date))
    )
    return df.loc[mask, ["location", "date", *columns]]


def has_data(df_filtered: pd.DataFrame, column: str, min_non_null: int = 1) -> bool:
    """Check whether a filtered slice has enough non-null values to chart."""
    return df_filtered[column].notna().sum() >= min_non_null


def latest_value(df_filtered: pd.DataFrame, location: str, column: str) -> float | None:
    """Return the most recent non-null value of a column for one location."""
    series = df_filtered.loc[df_filtered["location"] == location, column].dropna()
    return series.iloc[-1] if not series.empty else None


def country_snapshot(
    df: pd.DataFrame,
    column: str,
    start_date,
    end_date,
    continents: list[str] | None = None,
    locations: list[str] | None = None,
) -> pd.DataFrame:
    """Latest non-null value of `column` per real country/region within a date
    range, for a world map. Excludes OWID aggregates (no single shape to plot).
    Pass `continents` and/or `locations` to restrict the snapshot.
    """
    mask = (
        df["continent"].notna()
        & (df["date"] >= pd.Timestamp(start_date))
        & (df["date"] <= pd.Timestamp(end_date))
        & df[column].notna()
    )
    if continents:
        mask &= df["continent"].isin(continents)
    if locations:
        mask &= df["location"].isin(locations)
    sub = df.loc[mask, ["iso_code", "location", "continent", "date", column]]
    latest = sub.sort_values("date").groupby("location", observed=True).tail(1)
    return latest.drop(columns="date").reset_index(drop=True)


def vaccination_outcome_snapshot(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """Latest simultaneous (vaccination rate, death rate) reading per country
    within a date range, for the cross-country vaccination-effect scatter.
    """
    columns = ["people_fully_vaccinated_per_hundred", "total_deaths_per_million"]
    mask = (
        df["continent"].notna()
        & (df["date"] >= pd.Timestamp(start_date))
        & (df["date"] <= pd.Timestamp(end_date))
    )
    sub = df.loc[mask, ["location", "continent", "date", "population", *columns]].dropna(
        subset=columns
    )
    latest = sub.sort_values("date").groupby("location", observed=True).tail(1)
    return latest.drop(columns="date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_vaccine_cfr_summary(path: str = VACCINE_CFR_SUMMARY_PATH) -> pd.DataFrame:
    """Pre-computed before/after case-fatality-rate comparison for 7 locations,
    split at the date each one crossed 10% full vaccination coverage.
    """
    return pd.read_csv(
        path, parse_dates=["date_reached_10pct_fully_vaccinated", "data_as_of_date"]
    )


@st.cache_data(show_spinner="Loading vaccine manufacturer data...")
def load_vaccine_manufacturer_data(path: str = VACCINE_MANUFACTURER_PATH) -> pd.DataFrame:
    """OWID's by-manufacturer vaccination dataset: cumulative doses per vaccine
    brand, per location, per day. Covers ~44 mostly-European locations - a
    different, smaller set than the main OWID dataset.
    """
    df = pd.read_csv(path, parse_dates=["date"])
    df["location"] = df["location"].astype("category")
    df["vaccine"] = df["vaccine"].astype("category")
    return df


def latest_doses_by_vaccine(brand_df: pd.DataFrame) -> pd.DataFrame:
    """Total cumulative doses per vaccine brand, summed across every location
    in the manufacturer dataset (not a global total - only reporting locations).
    """
    latest = (
        brand_df.sort_values("date")
        .groupby(["location", "vaccine"], observed=True)
        .tail(1)
    )
    totals = (
        latest.groupby("vaccine", observed=True)["total_vaccinations"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    return totals
