"""Export the data app.py (the resilience app) needs from covid-resilience.db to small Parquet files.

covid-resilience.db is too large for GitHub (and is git-ignored), so the app reads
app-data/*.parquet instead; those files are committed. Re-run after rebuilding
the database:

    python build_resilience_db.py
    python export_app_data.py              # or: --db other.db --out other-dir
"""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from resilience import CAPACITY_COLUMNS, DATA_DIR, DAILY_COLUMNS, UN_MEMBER_ISO

DB_PATH = "covid-resilience.db"


def _in_un(column: str = "iso_code") -> tuple[str, tuple[str, ...]]:
    """SQL condition and parameters that keep only the 193 UN member states.

    Aggregates (World, continents, EU, income groups), territories, the UK nations,
    Taiwan, Kosovo, the Vatican and Palestine all drop out because their code is not in the list.
    """
    return f"{column} IN ({','.join('?' * len(UN_MEMBER_ISO))})", UN_MEMBER_ISO


def _query(select: str, table: str, column: str = "iso_code", extra: str = "") -> tuple[str, tuple[str, ...]]:
    condition, params = _in_un(column)
    return f"SELECT {select} FROM {table} WHERE {condition}{extra}", params


QUERIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "daily": _query(", ".join(DAILY_COLUMNS), "covid_data"),
    # GDP loss vs. the 2015-2019 trend per country (derived table, see sources.md)
    "gdp_loss": _query(
        "iso_code, cum_loss_2020_2023_pct_of_trend AS gdp_loss_trend_pct, growth_2020_pct, "
        "gdp_years_below_2019, gdp_recovery_year",
        "gdp_covid_loss",
        extra=" AND is_aggregate = 0",
    ),
    # School closures, unemployment rise, life-expectancy drop (derived table society_covid)
    "society": _query(
        "iso_code, school_weeks_full, school_weeks_partial_or_full, unemployment_rise_pp, "
        "life_expectancy_drop_years",
        "society_covid",
    ),
    # Pre-COVID healthcare capacity (derived table health_capacity, World Bank)
    "health_capacity": _query(f"iso_code, {', '.join(CAPACITY_COLUMNS)}", "health_capacity"),
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
