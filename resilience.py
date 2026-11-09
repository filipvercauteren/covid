"""Data and scoring functions for the "which countries coped best?" resilience app.

Pure functions over DataFrames read from app-data/*.parquet (exported from
covid-combo.db by export_app_data.py). No Streamlit imports,
so they can be reused from the notebook or tests.

Criteria (lower is better for all of them):
- health:    cumulative excess deaths per million up to a cutoff date, reported
             COVID deaths per million, or the drop in life expectancy 2019 -> worst
             of 2020-22
- economy:   cumulative GDP loss 2020-2023 vs. a "no COVID" baseline (table gdp_covid_loss):
             the IMF's October 2019 forecast (default) or the 2015-2019 trend
- jobs:      rise in unemployment 2019 -> worst of 2020-22, %-points (table society_covid)
- education: weeks with schools fully closed by requirement, 2020-22 (OxCGRT C1M = 3)
- freedom:   average OxCGRT stringency index 2020-2022 (how much restriction it took)
- recovery:  years in 2020-2024 with real GDP below its 2019 level (table gdp_covid_loss)

Healthcare capacity (table health_capacity, pre-COVID 2015-2019) is an explanatory
factor, not a criterion: see capacity_correlations().
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = "app-data"  # Parquet files written by export_app_data.py from covid-combo.db

# England, Scotland, Wales, Northern Ireland are already included in United Kingdom.
UK_NATIONS = ("OWID_ENG", "OWID_SCT", "OWID_WLS", "OWID_NIR")
# OWID invents codes where no ISO code exists; the World Bank uses XKX for Kosovo.
OWID_TO_WORLD_BANK_ISO = {"OWID_KOS": "XKX"}

FIRST_VACCINE_DATE = pd.Timestamp("2020-12-08")  # first dose outside trials (UK)
STRINGENCY_LAST_DATE = pd.Timestamp("2022-12-31")  # OxCGRT stopped tracking here
EXCESS_MAX_STALENESS = pd.DateOffset(months=6)  # last excess value must be this recent
VAX_THRESHOLD = 50.0  # % fully vaccinated for the "vaccination speed" measure

CUTOFFS = ("2020-12-31", "2021-12-31", "2022-12-31", "2023-12-31")

# What GDP would have been without COVID: baseline key -> (column, label)
GDP_BASELINES = {
    "imf": ("gdp_loss_imf_pct", "IMF forecast, Oct 2019"),
    "trend": ("gdp_loss_trend_pct", "Trend 2015–2019"),
}

HEALTH_MEASURES = {
    "excess_pm": "Excess deaths per million",
    "reported_pm": "Reported COVID deaths per million",
    "life_expectancy_drop_years": "Life-expectancy drop 2019 → 2020–22 (years)",
}

# criterion -> column; the health column is chosen by the user
COST_CRITERIA = {
    "economy": "gdp_loss_pct",
    "jobs": "unemployment_rise_pp",
    "education": "school_weeks_full",
    "freedom": "avg_stringency",
    "recovery": "gdp_years_below_2019",
}

CRITERIA_LABELS = {
    "health": "Health (deaths)",
    "economy": "Economy (GDP loss)",
    "jobs": "Jobs (unemployment rise)",
    "education": "Education (school closures)",
    "freedom": "Freedom (stringency)",
    "recovery": "Recovery (years GDP below 2019)",
}

# Pre-COVID healthcare capacity: higher = more capacity (explanatory, not scored)
CAPACITY_COLUMNS = {
    "health_spending_pct_gdp": "Health spending (% of GDP)",
    "health_spending_per_capita_usd": "Health spending per person (US$)",
    "physicians_per_1000": "Physicians per 1,000 people",
    "nurses_per_1000": "Nurses & midwives per 1,000 people",
    "hospital_beds_per_1000": "Hospital beds per 1,000 people",
}

COLUMN_LABELS = {
    **HEALTH_MEASURES,
    "gdp_loss_pct": "GDP loss 2020–23 vs. no-COVID baseline (%)",
    "gdp_loss_imf_pct": "GDP loss 2020–23 vs. IMF Oct 2019 forecast (%)",
    "gdp_loss_trend_pct": "GDP loss 2020–23 vs. 2015–19 trend (%)",
    "unemployment_rise_pp": "Unemployment rise 2019 → 2020–22 (%-points)",
    "school_weeks_full": "Weeks schools fully closed 2020–22",
    "school_weeks_partial_or_full": "Weeks schools partly or fully closed 2020–22",
    "avg_stringency": "Avg. stringency index 2020–22",
    "gdp_years_below_2019": "Years GDP below 2019 level (2020–24)",
    "gdp_recovery_year": "Year GDP back at 2019 level",
    **CAPACITY_COLUMNS,
    "pct_fully_vax": "% fully vaccinated",
    "days_to_50pct_vax": "Days to 50% fully vaccinated",
    "peak_icu_pm": "Peak ICU patients per million",
    "excess_vs_reported": "Excess ÷ reported deaths",
    "population": "Population",
}

DAILY_COLUMNS = (
    "iso_code",
    "location",
    "continent",
    "date",
    "population",
    "excess_mortality_cumulative_per_million",
    "total_deaths_per_million",
    "stringency_index",
    "people_fully_vaccinated_per_hundred",
    "icu_patients_per_million",
)


def _read(name: str, data_dir: str) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / f"{name}.parquet")


def load_daily(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Country-day rows for real countries only (see export_app_data.py for the filter)."""
    return _read("daily", data_dir)


def load_gdp_loss(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """GDP loss vs. pre-COVID trend per country (derived table, see sources.md)."""
    return _read("gdp_loss", data_dir)


def load_society(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """School closures, unemployment rise, life-expectancy drop (derived table society_covid)."""
    return _read("society", data_dir)


def load_health_capacity(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Pre-COVID healthcare capacity (derived table health_capacity, World Bank)."""
    return _read("health_capacity", data_dir)


def country_metrics(
    daily: pd.DataFrame,
    gdp: pd.DataFrame,
    society: pd.DataFrame,
    capacity: pd.DataFrame,
    cutoff: str,
) -> pd.DataFrame:
    """One row per country with every criterion, measured up to `cutoff`.

    - excess_pm: last cumulative excess deaths/million on or before the cutoff;
      NaN when that value is older than EXCESS_MAX_STALENESS (not comparable)
    - avg_stringency: mean over 2020-01-01 .. min(cutoff, 2022-12-31)
    - gdp_loss_pct, society columns: fixed periods (see module docstring),
      independent of the cutoff
    """
    cutoff_ts = pd.Timestamp(cutoff)
    upto = daily[daily["date"] <= cutoff_ts]
    by_country = upto.groupby("location")

    static = by_country.agg(
        iso_code=("iso_code", "first"),
        continent=("continent", "first"),
        population=("population", "max"),
        reported_pm=("total_deaths_per_million", "max"),
        pct_fully_vax=("people_fully_vaccinated_per_hundred", "max"),
        peak_icu_pm=("icu_patients_per_million", "max"),
    )

    last_excess = (
        upto.dropna(subset=["excess_mortality_cumulative_per_million"])
        .sort_values("date")
        .groupby("location")
        .tail(1)
        .set_index("location")
    )
    is_fresh = last_excess["date"] >= cutoff_ts - EXCESS_MAX_STALENESS

    avg_stringency = (
        upto[upto["date"] <= STRINGENCY_LAST_DATE].groupby("location")["stringency_index"].mean()
    )

    reached_threshold = (
        upto[upto["people_fully_vaccinated_per_hundred"] >= VAX_THRESHOLD]
        .groupby("location")["date"]
        .min()
    )

    metrics = static.assign(
        excess_pm=last_excess["excess_mortality_cumulative_per_million"].where(is_fresh),
        excess_last_date=last_excess["date"],
        avg_stringency=avg_stringency,
        days_to_50pct_vax=(reached_threshold - FIRST_VACCINE_DATE).dt.days,
    ).reset_index()

    metrics["wb_iso"] = metrics["iso_code"].replace(OWID_TO_WORLD_BANK_ISO)
    metrics = (
        metrics.merge(gdp, on="wb_iso", how="left")
        .merge(society, on="wb_iso", how="left")
        .merge(capacity, on="wb_iso", how="left")
        .drop(columns="wb_iso")
    )
    metrics["excess_vs_reported"] = metrics["excess_pm"] / metrics["reported_pm"]
    return metrics


def with_gdp_baseline(metrics: pd.DataFrame, baseline: str) -> pd.DataFrame:
    """Set gdp_loss_pct (the economy criterion) from the chosen baseline in GDP_BASELINES.
    Countries without that baseline get NaN - no silent fallback to the other method."""
    column, _ = GDP_BASELINES[baseline]
    return metrics.assign(gdp_loss_pct=metrics[column])


def select_peers(
    metrics: pd.DataFrame,
    min_population: int = 0,
    continents: tuple[str, ...] = (),
    countries: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Restrict to a peer group: explicit countries win over continents."""
    selected = metrics[metrics["population"] >= min_population]
    if countries:
        return selected[selected["location"].isin(countries)]
    if continents:
        return selected[selected["continent"].isin(continents)]
    return selected


def criterion_columns(health_column: str) -> dict[str, str]:
    return {"health": health_column, **COST_CRITERIA}


def _badness(values: pd.Series) -> pd.Series:
    """Rank-based 0 (best/lowest) .. 1 (worst/highest) within the group."""
    n = values.notna().sum()
    if n < 2:
        return values * 0.0
    return (values.rank(method="average") - 1) / (n - 1)


def score_countries(
    metrics: pd.DataFrame, health_column: str, weights: dict[str, float]
) -> tuple[pd.DataFrame, list[str]]:
    """Weighted combined score (100 = best on every active criterion, 0 = worst).

    Each criterion is converted to a within-group rank so units don't matter.
    Countries missing any criterion with a weight > 0 are left out and returned
    separately.
    """
    active = {name: w for name, w in weights.items() if w > 0}
    if not active:
        raise ValueError("At least one criterion needs a weight above 0.")

    columns = criterion_columns(health_column)
    used = [columns[name] for name in active]
    complete = metrics.dropna(subset=used)
    missing = sorted(set(metrics["location"]) - set(complete["location"]))

    total = sum(active.values())
    weighted_badness = sum(_badness(complete[columns[n]]) * w for n, w in active.items()) / total
    scored = complete.assign(
        score=100 * (1 - weighted_badness),
        **{f"rank_{n}": complete[columns[n]].rank(method="min") for n in active},
    )
    scored = scored.assign(rank=scored["score"].rank(ascending=False, method="min"))
    return scored.sort_values(["rank", "location"]), missing


def weight_grid(n_criteria: int, step: float = 0.1) -> np.ndarray:
    """Every weight combination for `n_criteria` criteria on a grid summing to 1."""
    units = round(1 / step)

    def compositions(remaining: int, parts: int) -> list[tuple[int, ...]]:
        if parts == 1:
            return [(remaining,)]
        return [
            (first, *rest)
            for first in range(remaining + 1)
            for rest in compositions(remaining - first, parts - 1)
        ]

    return np.array(compositions(units, n_criteria)) / units


def rank_stability(
    metrics: pd.DataFrame,
    health_column: str,
    criteria: list[str],
    step: float = 0.1,
    top_n: int = 10,
) -> tuple[pd.DataFrame, int]:
    """Rank of each country under every weight combination of `criteria`.

    A country that stays near the top whatever the weights is a robust result;
    one whose rank swings a lot depends on the chosen weights.
    """
    all_columns = criterion_columns(health_column)
    columns = [all_columns[c] for c in criteria]
    complete = metrics.dropna(subset=columns).reset_index(drop=True)
    grid = weight_grid(len(columns), step)
    if complete.empty:
        return complete.assign(best_rank=[], median_rank=[], worst_rank=[], pct_in_top=[]), len(grid)

    badness = np.column_stack([_badness(complete[c]).to_numpy() for c in columns])
    ranks = pd.DataFrame(badness @ grid.T).rank(method="min")  # one column per weight combo

    stability = complete[["location", "continent"]].assign(
        best_rank=ranks.min(axis=1),
        median_rank=ranks.median(axis=1),
        worst_rank=ranks.max(axis=1),
        pct_in_top=100 * (ranks <= top_n).mean(axis=1),
    )
    return stability.sort_values(["median_rank", "best_rank", "location"]), len(grid)


def capacity_correlations(
    metrics: pd.DataFrame, capacity_columns: list[str], outcome_columns: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Spearman rank correlation between capacity measures (rows) and outcomes (columns),
    plus the number of countries behind each value. Rank-based, so robust to outliers
    such as US health spending; pairwise, so each cell uses every country with both values."""
    corr = metrics[capacity_columns + outcome_columns].corr(method="spearman")
    present = metrics[capacity_columns + outcome_columns].notna().astype(int)
    counts = present.T @ present
    return (
        corr.loc[capacity_columns, outcome_columns],
        counts.loc[capacity_columns, outcome_columns],
    )


def excess_timeseries(daily: pd.DataFrame, locations: list[str]) -> pd.DataFrame:
    """Cumulative excess deaths per million over time for the given countries."""
    rows = daily[
        daily["location"].isin(locations) & daily["excess_mortality_cumulative_per_million"].notna()
    ]
    return rows[["location", "date", "excess_mortality_cumulative_per_million"]]


def vaccination_timeseries(daily: pd.DataFrame, locations: list[str]) -> pd.DataFrame:
    rows = daily[
        daily["location"].isin(locations) & daily["people_fully_vaccinated_per_hundred"].notna()
    ]
    return rows[["location", "date", "people_fully_vaccinated_per_hundred"]]
