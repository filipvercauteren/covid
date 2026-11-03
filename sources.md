# Data sources

All data used in `covid-combo.db` and `covid_analysis.ipynb`, with where it came from.
`build_combo_db.py` rebuilds the database from these sources (`--refresh` re-downloads them).
URLs were checked to be reachable on 2026-11-03.

## Loaded into `covid-combo.db`

| Table | Local file | Source | Retrieved |
|---|---|---|---|
| `covid_data` | `owid-covid-data.csv` | Our World in Data — COVID-19 dataset | 2026-08-24 |
| `vaccinations_by_manufacturer` | `vaccinations-by-manufacturer.csv` | Our World in Data — vaccinations by manufacturer | 2026-10-21 |
| `locations` | `locations.csv` | Our World in Data — vaccination locations / vaccines used | 2026-11-03 |
| `ve_primary_series`, `ve_booster` | `WeeklySummary_COVID19_VE_Studies_20250108.xlsx` | IVAC VIEW-hub (Johns Hopkins) — COVID-19 VE studies | 2026-11-03 |
| `gdp_annual` | `worldbank-gdp.csv` | World Bank — World Development Indicators API | 2026-11-03 |
| `gdp_covid_loss` | — | **Derived** from `gdp_annual` (see below) | 2026-11-03 |

### Our World in Data (OWID)

- Repository: https://github.com/owid/covid-19-data
- `owid-covid-data.csv`:
  https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv
- `vaccinations-by-manufacturer.csv`:
  https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/vaccinations/vaccinations-by-manufacturer.csv
- `locations.csv`:
  https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/vaccinations/locations.csv

OWID compiles data from other providers. Upstream sources of the columns used in the analysis:

| Column(s) in `covid_data` | Upstream source |
|---|---|
| `stringency_index` | Oxford COVID-19 Government Response Tracker (OxCGRT), Blavatnik School of Government — https://github.com/OxCGRT/covid-policy-dataset (older: https://github.com/OxCGRT/covid-policy-tracker). Coverage 2020-01-01 → 2022-12-31. |
| `excess_mortality*` | OWID excess-mortality dataset — https://github.com/owid/covid-19-data/tree/master/public/data/excess_mortality (built on the Human Mortality Database and the World Mortality Dataset) |
| `new_deaths`, `total_deaths`, cases | WHO COVID-19 dashboard (via OWID) |
| vaccination columns (`people_vaccinated`, …) | OWID vaccination dataset, from official national reporting |
| `population`, `aged_65_older`, `gdp_per_capita`, … | OWID / UN World Population Prospects / World Bank (static per country) |

`iso_code` values starting with `OWID_` are OWID-defined codes for aggregates (World, continents,
EU, income groups), UK nations, Kosovo (`OWID_KOS`) and Northern Cyprus (`OWID_CYN`).

### IVAC VIEW-hub — vaccine-effectiveness studies

- Page: https://view-hub.org/vaccine/covid/effectiveness-studies
- File: https://view-hub.org/sites/default/files/2026-01/WeeklySummary_COVID19_VE_Studies_20250108.xlsx
- Methods: https://view-hub.org/sites/default/files/2024-03/COVID19_VE_%26_Impact_Lit_Review_Methods.pdf
- Sheets loaded: "Primary Series Studies" → `ve_primary_series`, "Booster Studies" → `ve_booster`.
  Text columns were whitespace-trimmed; non-numeric `ve`/`lcl`/`ucl` values set to NULL
  (originals kept in `*_raw`).

### World Bank — World Development Indicators

- GDP (constant 2015 US$), `NY.GDP.MKTP.KD`:
  https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.KD?format=json&per_page=20000&date=2010:2025
- GDP growth (annual %), `NY.GDP.MKTP.KD.ZG`:
  https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=20000&date=2010:2025
- Country metadata (to flag aggregates): https://api.worldbank.org/v2/country?format=json&per_page=500
- Data last updated by the World Bank: 2026-10-08.

### Derived: `gdp_covid_loss`

Not a published dataset — calculated from `gdp_annual`:

1. Trend growth = `(GDP_2019 / GDP_2015)^(1/4) − 1`
2. Trend GDP for 2020–2023 = `GDP_2019 × (1 + trend)^(year − 2019)`
3. `cum_loss_2020_2023_pct_of_trend` = (Σ trend − Σ actual) / Σ trend × 100 over 2020–2023

Contains non-COVID shocks too (energy crisis 2022, wars, oil booms).

## Referenced but not loaded

| What | URL |
|---|---|
| Hong Kong CHP — deaths/cases by age × vaccine type × dose (PDF, 21 Dec 2022) | https://www.coronavirus.gov.hk/pdf/death_analysis/death_analysis_20221221.pdf |
| Hong Kong CHP — earlier editions | https://coronavirus.gov.hk/pdf/death_analysis/death_analysis_20221019.pdf, https://coronavirus.gov.hk/pdf/death_analysis/death_analysis_20220817.pdf |
| Malaysia MoH — individual death linelist with vaccine brand | https://github.com/MoH-Malaysia/covid19-public/blob/main/epidemic/linelist/linelist_deaths.csv |
| Malaysia MoH — daily doses by brand | https://github.com/MoH-Malaysia/covid19-public/blob/main/vaccination/vax_malaysia.csv |
| CDC — case/death rates by vaccination status (archived copy) | https://portal.datarescueproject.org/datasets/rates-of-covid-19-cases-or-deaths-by-age-group-and-vaccination-status/ |
| CDC MMWR — COVID-19 mortality and vaccine coverage, Hong Kong | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9020860/ |
