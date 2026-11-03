"""Data and scoring functions for the "which countries coped best?" resilience app.

Pure functions over DataFrames read from covid-combo.db. No Streamlit imports,
so they can be reused from the notebook or tests.

Criteria (lower is better for all of them):
- health:  cumulative excess deaths per million up to a cutoff date
           (optionally roughly age-adjusted), or reported COVID deaths per million
- economy: cumulative GDP loss 2020-2023 vs. the 2015-2019 trend (table gdp_covid_loss)
- freedom: average OxCGRT stringency index 2020-2022 (how much restriction it took)
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

import numpy as np
import pandas as pd

DB_PATH = "covid-combo.db"

# England, Scotland, Wales, Northern Ireland are already included in United Kingdom.
UK_NATIONS = ("OWID_ENG", "OWID_SCT", "OWID_WLS", "OWID_NIR")
# OWID invents codes where no ISO code exists; the World Bank uses XKX for Kosovo.
OWID_TO_WORLD_BANK_ISO = {"OWID_KOS": "XKX"}

FIRST_VACCINE_DATE = pd.Timestamp("2020-12-08")  # first dose outside trials (UK)
STRINGENCY_LAST_DATE = pd.Timestamp("2022-12-31")  # OxCGRT stopped tracking here
EXCESS_MAX_STALENESS = pd.DateOffset(months=6)  # last excess value must be this recent
VAX_THRESHOLD = 50.0  # % fully vaccinated for the "vaccination speed" measure

CUTOFFS = ("2020-12-31", "2021-12-31", "2022-12-31", "2023-12-31")

HEALTH_MEASURES = {
    "excess_pm": "Excess deaths per million",
    "excess_age_adj_pm": "Age-adjusted excess deaths per million",
    "reported_pm": "Reported COVID deaths per million",
}

CRITERIA_LABELS = {
    "health": "Health (deaths)",
    "economy": "Economy (GDP loss)",
    "freedom": "Freedom (stringency)",
}

COLUMN_LABELS = {
    **HEALTH_MEASURES,
    "gdp_loss_pct": "GDP loss vs. trend 2020–23 (%)",
    "avg_stringency": "Avg. stringency index 2020–22",
    "pct_fully_vax": "% fully vaccinated",
    "pct_65plus": "% aged 65+",
    "days_to_50pct_vax": "Days to 50% fully vaccinated",
    "peak_icu_pm": "Peak ICU patients per million",
    "excess_vs_reported": "Excess ÷ reported deaths",
    "population": "Population",
}

_DAILY_COLUMNS = (
    "iso_code",
    "location",
    "continent",
    "date",
    "population",
    "aged_65_older",
    "excess_mortality_cumulative_per_million",
    "total_deaths_per_million",
    "stringency_index",
    "people_fully_vaccinated_per_hundred",
    "icu_patients_per_million",
)


def load_daily(db_path: str = DB_PATH) -> pd.DataFrame:
    """Country-day rows for real countries only.

    Aggregates (World, continents, EU, income groups) have no continent; the UK
    nations are dropped because United Kingdom already covers them. Kosovo and
    Northern Cyprus are kept even though their iso_code starts with OWID_.
    """
    placeholders = ",".join("?" * len(UK_NATIONS))
    query = f"""
        SELECT {", ".join(_DAILY_COLUMNS)}
        FROM covid_data
        WHERE continent IS NOT NULL AND iso_code NOT IN ({placeholders})
    """
    with closing(sqlite3.connect(db_path)) as conn:
        return pd.read_sql(query, conn, params=UK_NATIONS, parse_dates=["date"])


def load_gdp_loss(db_path: str = DB_PATH) -> pd.DataFrame:
    """GDP loss vs. pre-COVID trend per country (derived table, see sources.md)."""
    query = """
        SELECT iso_code AS wb_iso,
               cum_loss_2020_2023_pct_of_trend AS gdp_loss_pct,
               growth_2020_pct
        FROM gdp_covid_loss
        WHERE is_aggregate = 0
    """
    with closing(sqlite3.connect(db_path)) as conn:
        return pd.read_sql(query, conn)


def country_metrics(daily: pd.DataFrame, gdp: pd.DataFrame, cutoff: str) -> pd.DataFrame:
    """One row per country with every criterion, measured up to `cutoff`.

    - excess_pm: last cumulative excess deaths/million on or before the cutoff;
      NaN when that value is older than EXCESS_MAX_STALENESS (not comparable)
    - avg_stringency: mean over 2020-01-01 .. min(cutoff, 2022-12-31)
    - gdp_loss_pct: always 2020-2023, independent of the cutoff
    """
    cutoff_ts = pd.Timestamp(cutoff)
    upto = daily[daily["date"] <= cutoff_ts]
    by_country = upto.groupby("location")

    static = by_country.agg(
        iso_code=("iso_code", "first"),
        continent=("continent", "first"),
        population=("population", "max"),
        pct_65plus=("aged_65_older", "max"),
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
    metrics = metrics.merge(gdp, on="wb_iso", how="left").drop(columns="wb_iso")
    metrics["excess_vs_reported"] = metrics["excess_pm"] / metrics["reported_pm"]
    return metrics


def add_age_adjusted_excess(metrics: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    """Rough age correction: fit excess_pm = a + b × %65+ across `metrics` and
    shift every country to the group's average share of over-65s.

    Returns (metrics with excess_age_adj_pm, slope b, correlation). Only a crude
    correction - age-standardised mortality data would be better.
    """
    fit = metrics.dropna(subset=["excess_pm", "pct_65plus"])
    if len(fit) < 3:
        return metrics.assign(excess_age_adj_pm=np.nan), float("nan"), float("nan")

    slope, _ = np.polyfit(fit["pct_65plus"], fit["excess_pm"], 1)
    corr = float(np.corrcoef(fit["pct_65plus"], fit["excess_pm"])[0, 1])
    adjusted = metrics["excess_pm"] - slope * (metrics["pct_65plus"] - fit["pct_65plus"].mean())
    return metrics.assign(excess_age_adj_pm=adjusted), float(slope), corr


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
    return {"health": health_column, "economy": "gdp_loss_pct", "freedom": "avg_stringency"}


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


def weight_grid(step: float = 0.1) -> np.ndarray:
    """Every (health, economy, freedom) weight combination on a grid summing to 1."""
    n = round(1 / step)
    return np.array(
        [(h / n, e / n, (n - h - e) / n) for h in range(n + 1) for e in range(n + 1 - h)]
    )


def rank_stability(
    metrics: pd.DataFrame, health_column: str, step: float = 0.1, top_n: int = 10
) -> tuple[pd.DataFrame, int]:
    """Rank of each country under every weight combination in `weight_grid`.

    A country that stays near the top whatever the weights is a robust result;
    one whose rank swings a lot depends on the chosen weights.
    """
    columns = list(criterion_columns(health_column).values())
    complete = metrics.dropna(subset=columns).reset_index(drop=True)
    grid = weight_grid(step)
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
