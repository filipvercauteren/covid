"""Build covid-combo.db: the SQLite database behind covid_analysis.ipynb and resilience_app.py.

Usage:
    python build_combo_db.py              # use local files, download what's missing
    python build_combo_db.py --refresh    # re-download every downloadable source
    python build_combo_db.py --db other.db

Tables (see sources.md for URLs and provenance):
    covid_data                    owid-covid-data.csv                (local file, required)
    vaccinations_by_manufacturer  vaccinations-by-manufacturer.csv   (downloaded if missing)
    locations                     locations.csv                      (downloaded if missing)
    ve_primary_series, ve_booster VIEW-hub VE studies .xlsx          (downloaded if missing)
    gdp_annual                    worldbank-gdp.csv / World Bank API (downloaded if missing)
    gdp_covid_loss                derived from gdp_annual

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

DB_PATH = "covid-combo.db"

OWID_RAW = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data"
COVID_CSV = "owid-covid-data.csv"
MANUFACTURER_CSV = "vaccinations-by-manufacturer.csv"
MANUFACTURER_URL = f"{OWID_RAW}/vaccinations/vaccinations-by-manufacturer.csv"
LOCATIONS_CSV = "locations.csv"
LOCATIONS_URL = f"{OWID_RAW}/vaccinations/locations.csv"
VIEWHUB_XLSX = "WeeklySummary_COVID19_VE_Studies_20250108.xlsx"
VIEWHUB_URL = f"https://view-hub.org/sites/default/files/2026-01/{VIEWHUB_XLSX}"
GDP_CSV = "worldbank-gdp.csv"

WORLD_BANK_API = "https://api.worldbank.org/v2"
GDP_INDICATORS = {
    "NY.GDP.MKTP.KD": "gdp_constant_2015_usd",
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
}
GDP_YEARS = "2010:2025"

TREND_START, TREND_END = 2015, 2019
LOSS_YEARS = (2020, 2021, 2022, 2023)

USER_AGENT = "covid-combo-db-builder"


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
    url = f"{WORLD_BANK_API}/country/all/indicator/{indicator}?format=json&per_page=20000&date={GDP_YEARS}"
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


def ensure_gdp_csv(refresh: bool) -> pd.DataFrame:
    """World Bank real GDP + growth per country/year, cached in worldbank-gdp.csv."""
    target = Path(GDP_CSV)
    if target.exists() and not refresh:
        return pd.read_csv(target)

    frames = [fetch_world_bank_indicator(ind, col) for ind, col in GDP_INDICATORS.items()]
    gdp = frames[0].merge(frames[1], on=["iso_code", "country", "year"], how="outer")
    gdp = gdp[gdp["iso_code"].fillna("") != ""]
    gdp["is_aggregate"] = gdp["iso_code"].isin(fetch_world_bank_aggregates()).astype(int)
    gdp = gdp.sort_values(["iso_code", "year"])
    gdp.to_csv(target, index=False)
    return gdp


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
        }
    )


def gdp_covid_loss(gdp: pd.DataFrame) -> pd.DataFrame:
    columns = ["year", "gdp_constant_2015_usd", "gdp_growth_pct"]
    return (
        gdp.groupby(["iso_code", "country", "is_aggregate"])[columns]
        .apply(gdp_loss_for_country)
        .dropna(how="all")
        .reset_index()
    )


# ---------------------------------------------------------------- build

def load_tables(refresh: bool) -> dict[str, pd.DataFrame]:
    if not Path(COVID_CSV).exists():
        raise SystemExit(f"{COVID_CSV} not found - download it first (see sources.md).")

    print("Reading sources")
    viewhub = ensure_file(VIEWHUB_XLSX, VIEWHUB_URL, refresh)
    gdp = ensure_gdp_csv(refresh)
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
    }


INDEXES = (
    "CREATE INDEX idx_covid_loc_date ON covid_data(location, date)",
    "CREATE INDEX idx_vacc_loc_date ON vaccinations_by_manufacturer(location, date)",
    "CREATE INDEX idx_locations_location ON locations(location)",
    "CREATE INDEX idx_vep ON ve_primary_series(primary_series_vaccine, outcome_category)",
    "CREATE INDEX idx_veb ON ve_booster(booster_vaccine, outcome_category)",
    "CREATE INDEX idx_gdp_iso_year ON gdp_annual(iso_code, year)",
    "CREATE INDEX idx_gdploss_iso ON gdp_covid_loss(iso_code)",
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
