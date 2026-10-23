"""One-off build step: mirror owid-covid-data.csv into a SQLite database.

Not imported by the app - run manually whenever the CSV changes, then commit
the resulting owid-covid-data.db. Lets you query the dataset with real SQL
(sqlite3 CLI, a notebook, DB Browser for SQLite, ...) without touching the
dashboard's own fast Parquet-based loading path.
"""

import sqlite3

import pandas as pd

CSV_PATH = "owid-covid-data.csv"
DB_PATH = "owid-covid-data.db"
TABLE_NAME = "covid_data"


def build() -> None:
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])

    float_cols = df.select_dtypes(include="float64").columns
    df[float_cols] = df[float_cols].astype("float32")

    for col in ("iso_code", "continent", "location", "tests_units"):
        df[col] = df[col].astype("category")

    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql(TABLE_NAME, conn, index=False, if_exists="replace")

    print(f"Wrote {len(df)} rows to {DB_PATH} ({TABLE_NAME})")


if __name__ == "__main__":
    build()
