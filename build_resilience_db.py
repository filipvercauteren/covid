"""Build covid-resilience.db: the SQLite database behind covid_analysis.ipynb and app.py (the resilience app).

Usage:
    python build_resilience_db.py              # use local files, download what's missing
    python build_resilience_db.py --refresh    # re-download every downloadable source
    python build_resilience_db.py --db other.db

Tables (see sources.md for URLs and provenance):
    covid_data                    owid-covid-data.csv                (local file, required)
    vaccinations_by_manufacturer  vaccinations-by-manufacturer.csv   (downloaded if missing)
    locations                     locations.csv                      (downloaded if missing)
    ve_primary_series, ve_booster VIEW-hub VE studies .xlsx          (downloaded if missing)
    gdp_annual                    worldbank-gdp.csv / World Bank API (downloaded if missing)
    gdp_covid_loss                derived from gdp_annual: GDP loss 2020-2023 vs. the
                                  2015-2019 trend, recovery time
    oxcgrt_daily                  OxCGRT national policy indicators  (downloaded if missing)
    social_annual                 worldbank-social.csv / World Bank API: unemployment,
                                  life expectancy                    (downloaded if missing)
    society_covid                 derived: school-closure weeks, unemployment rise,
                                  life-expectancy drop per country
    health_annual                 worldbank-health.csv / World Bank API: health spending,
                                  physicians, nurses, hospital beds  (downloaded if missing)
    health_capacity               derived: latest pre-COVID (2015-2019) value per country

The database is written to a temporary file first and only replaces the
existing one when every step succeeded.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import urllib.request
from contextlib import closing
from pathlib import Path

import numpy as np
import pandas as pd

DB_PATH = "covid-resilience.db"

OWID_RAW = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data"
COVID_CSV = "owid-covid-data.csv"
MANUFACTURER_CSV = "vaccinations-by-manufacturer.csv"
MANUFACTURER_URL = f"{OWID_RAW}/vaccinations/vaccinations-by-manufacturer.csv"
LOCATIONS_CSV = "locations.csv"
LOCATIONS_URL = f"{OWID_RAW}/vaccinations/locations.csv"
VIEWHUB_XLSX = "WeeklySummary_COVID19_VE_Studies_20250108.xlsx"
VIEWHUB_URL = f"https://view-hub.org/sites/default/files/2026-01/{VIEWHUB_XLSX}"
GDP_CSV = "worldbank-gdp.csv"
SOCIAL_CSV = "worldbank-social.csv"
HEALTH_CSV = "worldbank-health.csv"
OXCGRT_CSV = "OxCGRT_compact_national_v1.csv"
OXCGRT_URL = f"https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/{OXCGRT_CSV}"

WORLD_BANK_API = "https://api.worldbank.org/v2"
GDP_INDICATORS = {
    "NY.GDP.MKTP.KD": "gdp_constant_2015_usd",
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
}
SOCIAL_INDICATORS = {
    "SL.UEM.TOTL.ZS": "unemployment_pct",  # modeled ILO estimate, % of labour force
    "SP.DYN.LE00.IN": "life_expectancy_years",
}
HEALTH_INDICATORS = {
    "SH.XPD.CHEX.GD.ZS": "health_spending_pct_gdp",
    "SH.XPD.CHEX.PC.CD": "health_spending_per_capita_usd",
    "SH.MED.PHYS.ZS": "physicians_per_1000",
    "SH.MED.NUMW.P3": "nurses_per_1000",
    "SH.MED.BEDS.ZS": "hospital_beds_per_1000",
}
HEALTH_BASELINE_YEARS = (2015, 2019)  # latest value in this range = pre-COVID capacity
WORLD_BANK_YEARS = "2010:2025"

TREND_START, TREND_END = 2015, 2019
LOSS_YEARS = (2020, 2021, 2022, 2023)
RECOVERY_YEARS = (2020, 2021, 2022, 2023, 2024)  # window for "years below the 2019 level"
RECOVERY_SEARCH_LAST_YEAR = 2025  # latest year searched for the recovery year

BASELINE_YEAR = 2019
SOCIETY_YEARS = (2020, 2021, 2022)
# OxCGRT C1M school closing: 0 none, 1 recommended, 2 required for some levels, 3 required for all levels
SCHOOL_PARTIAL, SCHOOL_FULL = 2, 3

USER_AGENT = "covid-resilience-db-builder"


# ---------------------------------------------------------------- downloading

def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def ensure_file(path: str, url: str, refresh: bool) -> Path:
    """Return `path`, downloading it from `url` first if missing or refresh is set."""
    target = Path(path)
    if refresh or not target.exists():
        print(f"  downloading {url}")
        target.write_bytes(fetch_bytes(url))
    return target


def fetch_world_bank_indicator(indicator: str, column: str) -> pd.DataFrame:
    url = f"{WORLD_BANK_API}/country/all/indicator/{indicator}?format=json&per_page=20000&date={WORLD_BANK_YEARS}"
    print(f"  downloading {url}")
    _, rows = json.loads(fetch_bytes(url))
    return pd.DataFrame(
        [
            {
                "iso_code": r["countryiso3code"],
                "country": r["country"]["value"],
                "year": int(r["date"]),
                column: r["value"],
            }
            for r in rows
        ]
    )


def fetch_world_bank_aggregates() -> set[str]:
    _, countries = json.loads(fetch_bytes(f"{WORLD_BANK_API}/country?format=json&per_page=500"))
    return {c["id"] for c in countries if c["region"]["value"] == "Aggregates"}


def ensure_world_bank_csv(path: str, indicators: dict[str, str], refresh: bool) -> pd.DataFrame:
    """World Bank indicators per country/year (one column each), cached in `path`."""
    target = Path(path)
    if target.exists() and not refresh:
        return pd.read_csv(target)

    keys = ["iso_code", "country", "year"]
    frames = [fetch_world_bank_indicator(ind, col) for ind, col in indicators.items()]
    data = frames[0]
    for frame in frames[1:]:
        data = data.merge(frame, on=keys, how="outer")
    data = data[data["iso_code"].fillna("") != ""]
    data["is_aggregate"] = data["iso_code"].isin(fetch_world_bank_aggregates()).astype(int)
    data = data.sort_values(["iso_code", "year"])
    data.to_csv(target, index=False)
    return data


# ---------------------------------------------------------------- transforms

def clean_viewhub_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """snake_case column names, trimmed text, numeric VE/LCL/UCL (originals kept in *_raw)."""
    df = df.rename(columns=lambda c: re.sub(r"\W+", "_", str(c).strip()).strip("_").lower())
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    # Columns can mix numbers and text (e.g. dose_number "1", 2, "final"): only strip
    # real strings - Series.str.strip() would turn the numbers into NaN.
    df[text_columns] = df[text_columns].apply(
        lambda s: s.map(lambda v: v.strip() if isinstance(v, str) else v)
    )
    for column in ("ve", "lcl", "ucl"):
        df[f"{column}_raw"] = df[column].astype(str)
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def gdp_loss_for_country(group: pd.DataFrame) -> pd.Series | None:
    """GDP shortfall vs. the 2015-2019 trend extended over 2020-2023.

    trend growth  g        = (GDP_2019 / GDP_2015)^(1/4) - 1
    trend GDP     T_y      = GDP_2019 * (1 + g)^(y - 2019)
    cumulative loss        = (sum T_y - sum GDP_y) / sum T_y   over 2020-2023
    """
    gdp = group.set_index("year")["gdp_constant_2015_usd"]
    needed = (TREND_START, TREND_END, *LOSS_YEARS)
    if not all(year in gdp.index and pd.notna(gdp[year]) for year in needed):
        return None

    years = list(LOSS_YEARS)
    trend_growth = (gdp[TREND_END] / gdp[TREND_START]) ** (1 / (TREND_END - TREND_START)) - 1
    trend = pd.Series({y: gdp[TREND_END] * (1 + trend_growth) ** (y - TREND_END) for y in years})
    actual = gdp[years]
    shortfall = trend.sum() - actual.sum()

    return pd.Series(
        {
            "trend_growth_2015_2019_pct": 100 * trend_growth,
            "growth_2020_pct": group.set_index("year")["gdp_growth_pct"].get(2020),
            **{f"gap_vs_trend_{y}_pct": 100 * (actual[y] / trend[y] - 1) for y in years},
            "cum_loss_2020_2023_pct_of_trend": 100 * shortfall / trend.sum(),
            "cum_loss_2020_2023_pct_of_2019_gdp": 100 * shortfall / gdp[TREND_END],
            "gdp_2023_vs_2019_pct": 100 * (actual[2023] / gdp[TREND_END] - 1),
            **gdp_recovery(gdp),
        }
    )


def gdp_recovery(gdp: pd.Series) -> dict[str, float]:
    """How quickly real GDP got back to its 2019 level.

    gdp_years_below_2019: years in 2020-2024 with GDP below 2019 (0-5; lower = more
                          resilient; also counts later dips). NaN if 2024 is missing.
    gdp_recovery_year:    first year from 2020 with GDP >= 2019 level; NaN if not
                          back by the latest available year (up to 2025).
    """
    baseline = gdp[TREND_END]
    window = [y for y in RECOVERY_YEARS if y in gdp.index and pd.notna(gdp[y])]
    years_below = (
        float(sum(gdp[y] < baseline for y in window))
        if len(window) == len(RECOVERY_YEARS)
        else np.nan
    )
    recovered = [
        y
        for y in range(RECOVERY_YEARS[0], RECOVERY_SEARCH_LAST_YEAR + 1)
        if y in gdp.index and pd.notna(gdp[y]) and gdp[y] >= baseline
    ]
    return {
        "gdp_years_below_2019": years_below,
        "gdp_recovery_year": float(recovered[0]) if recovered else np.nan,
    }


def gdp_covid_loss(gdp: pd.DataFrame) -> pd.DataFrame:
    """Per country: GDP loss 2020-2023 vs. the 2015-2019 trend, plus recovery time."""
    columns = ["year", "gdp_constant_2015_usd", "gdp_growth_pct"]
    return (
        gdp.groupby(["iso_code", "country", "is_aggregate"])[columns]
        .apply(gdp_loss_for_country)
        .dropna(how="all")
        .reset_index()
    )


def clean_oxcgrt(raw: pd.DataFrame) -> pd.DataFrame:
    """National totals only, snake_case columns, real dates.

    "C1M_School closing" -> c1m_school_closing, "C1M_Flag" -> c1m_flag, ...
    """
    national = raw[raw["Jurisdiction"] == "NAT_TOTAL"].drop(
        columns=["RegionName", "RegionCode", "Jurisdiction"], errors="ignore"
    )
    national = national.rename(
        columns=lambda c: re.sub(r"[^0-9a-z]+", "_", c.lower()).strip("_")
    ).rename(columns={"countrycode": "iso_code", "countryname": "country"})
    national["date"] = pd.to_datetime(national["date"].astype(str), format="%Y%m%d")
    return national


def school_closure_weeks(oxcgrt: pd.DataFrame) -> pd.DataFrame:
    """Weeks with schools closed by requirement, from OxCGRT C1M, 2020-2022.

    full:           C1M = 3 (closing required at all levels)
    partial_or_full: C1M >= 2 (closing required at some or all levels)
    """
    level = oxcgrt["c1m_school_closing"]
    days = oxcgrt.assign(full=level >= SCHOOL_FULL, partial_or_full=level >= SCHOOL_PARTIAL)
    counted = days[level.notna()].groupby("iso_code")[["full", "partial_or_full"]].sum() / 7
    return counted.rename(
        columns={"full": "school_weeks_full", "partial_or_full": "school_weeks_partial_or_full"}
    )


def social_changes(social: pd.DataFrame) -> pd.DataFrame:
    """Per country, vs. 2019: worst unemployment rise and worst life-expectancy drop in 2020-2022."""
    countries = social[social["is_aggregate"] == 0]
    wide = countries.pivot_table(
        index="iso_code", columns="year", values=["unemployment_pct", "life_expectancy_years"]
    )
    years = [y for y in SOCIETY_YEARS if y in wide["unemployment_pct"].columns]
    unemployment, life = wide["unemployment_pct"], wide["life_expectancy_years"]
    return pd.DataFrame(
        {
            "unemployment_2019_pct": unemployment[BASELINE_YEAR],
            "unemployment_rise_pp": unemployment[years].max(axis=1) - unemployment[BASELINE_YEAR],
            "life_expectancy_2019": life[BASELINE_YEAR],
            "life_expectancy_drop_years": life[BASELINE_YEAR] - life[years].min(axis=1),
        }
    )


def health_capacity(health: pd.DataFrame) -> pd.DataFrame:
    """Pre-COVID healthcare capacity: per indicator, the latest value in 2015-2019
    (and the year it is from, since physicians/beds are not reported every year)."""
    first, last = HEALTH_BASELINE_YEARS
    baseline = health[
        (health["is_aggregate"] == 0) & health["year"].between(first, last)
    ].sort_values("year")

    def latest(column: str) -> pd.DataFrame:
        rows = baseline.dropna(subset=[column]).groupby("iso_code").tail(1).set_index("iso_code")
        return rows[[column, "year"]].rename(columns={"year": f"{column}_year"})

    names = health[health["is_aggregate"] == 0].drop_duplicates("iso_code").set_index("iso_code")["country"]
    capacity = pd.concat([latest(c) for c in HEALTH_INDICATORS.values()], axis=1)
    return capacity.join(names).reset_index()[["iso_code", "country", *capacity.columns]]


def society_covid(oxcgrt: pd.DataFrame, social: pd.DataFrame) -> pd.DataFrame:
    """One row per country (ISO3 code as used by OxCGRT and the World Bank)."""
    names = pd.concat(
        [
            social[social["is_aggregate"] == 0][["iso_code", "country"]],
            oxcgrt[["iso_code", "country"]],
        ]
    ).drop_duplicates("iso_code").set_index("iso_code")["country"]
    combined = school_closure_weeks(oxcgrt).join(social_changes(social), how="outer")
    return combined.join(names).reset_index()[["iso_code", "country", *combined.columns]]


# ---------------------------------------------------------------- build

def load_tables(refresh: bool) -> dict[str, pd.DataFrame]:
    if not Path(COVID_CSV).exists():
        raise SystemExit(f"{COVID_CSV} not found - download it first (see sources.md).")

    print("Reading sources")
    viewhub = ensure_file(VIEWHUB_XLSX, VIEWHUB_URL, refresh)
    gdp = ensure_world_bank_csv(GDP_CSV, GDP_INDICATORS, refresh)
    social = ensure_world_bank_csv(SOCIAL_CSV, SOCIAL_INDICATORS, refresh)
    health = ensure_world_bank_csv(HEALTH_CSV, HEALTH_INDICATORS, refresh)
    oxcgrt = clean_oxcgrt(pd.read_csv(ensure_file(OXCGRT_CSV, OXCGRT_URL, refresh), low_memory=False))
    return {
        "covid_data": pd.read_csv(COVID_CSV, parse_dates=["date"]),
        "vaccinations_by_manufacturer": pd.read_csv(
            ensure_file(MANUFACTURER_CSV, MANUFACTURER_URL, refresh), parse_dates=["date"]
        ),
        "locations": pd.read_csv(
            ensure_file(LOCATIONS_CSV, LOCATIONS_URL, refresh), parse_dates=["last_observation_date"]
        ),
        "ve_primary_series": clean_viewhub_sheet(pd.read_excel(viewhub, sheet_name="Primary Series Studies")),
        "ve_booster": clean_viewhub_sheet(pd.read_excel(viewhub, sheet_name="Booster Studies")),
        "gdp_annual": gdp,
        "gdp_covid_loss": gdp_covid_loss(gdp),
        "oxcgrt_daily": oxcgrt,
        "social_annual": social,
        "society_covid": society_covid(oxcgrt, social),
        "health_annual": health,
        "health_capacity": health_capacity(health),
    }


INDEXES = (
    "CREATE INDEX idx_covid_loc_date ON covid_data(location, date)",
    "CREATE INDEX idx_vacc_loc_date ON vaccinations_by_manufacturer(location, date)",
    "CREATE INDEX idx_locations_location ON locations(location)",
    "CREATE INDEX idx_vep ON ve_primary_series(primary_series_vaccine, outcome_category)",
    "CREATE INDEX idx_veb ON ve_booster(booster_vaccine, outcome_category)",
    "CREATE INDEX idx_gdp_iso_year ON gdp_annual(iso_code, year)",
    "CREATE INDEX idx_gdploss_iso ON gdp_covid_loss(iso_code)",
    "CREATE INDEX idx_oxcgrt_iso_date ON oxcgrt_daily(iso_code, date)",
    "CREATE INDEX idx_social_iso_year ON social_annual(iso_code, year)",
    "CREATE INDEX idx_society_iso ON society_covid(iso_code)",
    "CREATE INDEX idx_health_iso_year ON health_annual(iso_code, year)",
    "CREATE INDEX idx_health_capacity_iso ON health_capacity(iso_code)",
)


def write_database(tables: dict[str, pd.DataFrame], db_path: str) -> None:
    tmp_path = Path(f"{db_path}.tmp")
    tmp_path.unlink(missing_ok=True)

    print(f"Writing {db_path}")
    with closing(sqlite3.connect(tmp_path)) as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, index=False)
            print(f"  {name:<30} {len(df):>9,} rows")
        for statement in INDEXES:
            conn.execute(statement)
        conn.commit()

    os.replace(tmp_path, db_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default=DB_PATH, help=f"output database (default {DB_PATH})")
    parser.add_argument("--refresh", action="store_true", help="re-download all downloadable sources")
    args = parser.parse_args()

    write_database(load_tables(args.refresh), args.db)
    print("Done.")


if __name__ == "__main__":
    main()
