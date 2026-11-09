"""Export the data app.py (the resilience app) needs from covid-combo.db to small Parquet files.

covid-combo.db is too large for GitHub (and is git-ignored), so the app reads
app-data/*.parquet instead; those files are committed. Re-run after rebuilding
the database:

    python build_combo_db.py
    python export_app_data.py              # or: --db other.db --out other-dir
"""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from resilience import CAPACITY_COLUMNS, DATA_DIR, DAILY_COLUMNS, UK_NATIONS

DB_PATH = "covid-combo.db"


def _daily_query() -> tuple[str, tuple[str, ...]]:
    """Country-day rows for real countries only.

    Aggregates (World, continents, EU, income groups) have no continent; the UK
    nations are dropped because United Kingdom already covers them. Kosovo and
    Northern Cyprus are kept even though their iso_code starts with OWID_.
    """
    placeholders = ",".join("?" * len(UK_NATIONS))
    query = f"""
        SELECT {", ".join(DAILY_COLUMNS)}
        FROM covid_data
        WHERE continent IS NOT NULL AND iso_code NOT IN ({placeholders})
    """
    return query, UK_NATIONS


QUERIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "daily": _daily_query(),
    # GDP loss vs. pre-COVID trend per country (derived table, see sources.md)
    "gdp_loss": (
        """
        SELECT iso_code AS wb_iso,
               imf_cum_loss_2020_2023_pct AS gdp_loss_imf_pct,
               cum_loss_2020_2023_pct_of_trend AS gdp_loss_trend_pct,
               growth_2020_pct, gdp_years_below_2019, gdp_recovery_year
        FROM gdp_covid_loss
        WHERE is_aggregate = 0
        """,
        (),
    ),
    # School closures, unemployment rise, life-expectancy drop (derived table society_covid)
    "society": (
        """
        SELECT iso_code AS wb_iso, school_weeks_full, school_weeks_partial_or_full,
               unemployment_rise_pp, life_expectancy_drop_years
        FROM society_covid
        """,
        (),
    ),
    # Pre-COVID healthcare capacity (derived table health_capacity, World Bank)
    "health_capacity": (
        f"SELECT iso_code AS wb_iso, {', '.join(CAPACITY_COLUMNS)} FROM health_capacity",
        (),
    ),
}


def export(db_path: str, out_dir: str) -> list[Path]:
    """Write one Parquet file per entry in QUERIES and return their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        frames = {
            name: pd.read_sql(query, conn, params=params, parse_dates=["date"] if name == "daily" else None)
            for name, (query, params) in QUERIES.items()
        }
    paths = [out / f"{name}.parquet" for name in frames]
    for path, frame in zip(paths, frames.values()):
        frame.to_parquet(path, index=False, compression="zstd")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=DB_PATH, help=f"source SQLite database (default {DB_PATH})")
    parser.add_argument("--out", default=DATA_DIR, help=f"output directory (default {DATA_DIR})")
    args = parser.parse_args()
    for path in export(args.db, args.out):
        print(f"{path}  {path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
