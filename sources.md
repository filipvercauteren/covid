# Data sources

All data used in `covid-resilience.db` and `covid_analysis.ipynb`, with where it came from.
`build_resilience_db.py` rebuilds the database from these sources (`--refresh` re-downloads them).
URLs were checked to be reachable on 2026-11-03.

## Loaded into `covid-resilience.db`

| Table | Local file | Source | Retrieved |
|---|---|---|---|
| `covid_data` | `owid-covid-data.csv` | Our World in Data — COVID-19 dataset | 2026-08-24 |
| `vaccinations_by_manufacturer` | `vaccinations-by-manufacturer.csv` | Our World in Data — vaccinations by manufacturer | 2026-10-21 |
| `locations` | `locations.csv` | Our World in Data — vaccination locations / vaccines used | 2026-11-03 |
| `ve_primary_series`, `ve_booster` | `WeeklySummary_COVID19_VE_Studies_20250108.xlsx` | IVAC VIEW-hub (Johns Hopkins) — COVID-19 VE studies | 2026-11-03 |
| `gdp_annual` | `worldbank-gdp.csv` | World Bank — World Development Indicators API | 2026-11-03 |
| `gdp_covid_loss` | — | **Derived** from `gdp_annual` (see below) | 2026-11-03 |
| `oxcgrt_daily` | `OxCGRT_compact_national_v1.csv` (not in git, 44 MB) | Oxford COVID-19 Government Response Tracker | 2026-11-03 |
| `social_annual` | `worldbank-social.csv` | World Bank — unemployment, life expectancy | 2026-11-03 |
| `society_covid` | — | **Derived** from `oxcgrt_daily` and `social_annual` (see below) | 2026-11-03 |
| `health_annual` | `worldbank-health.csv` | World Bank — health spending, physicians, nurses, hospital beds | 2026-11-03 |
| `health_capacity` | — | **Derived** from `health_annual` (see below) | 2026-11-03 |

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

Recovery columns in the same table:

- `gdp_years_below_2019` — number of years in 2020–2024 with real GDP below its 2019 level (0–5)
- `gdp_recovery_year` — first year from 2020 with real GDP back at or above 2019 (NULL if not yet)

### OxCGRT — Oxford COVID-19 Government Response Tracker

- Repository: https://github.com/OxCGRT/covid-policy-dataset
- File: https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/OxCGRT_compact_national_v1.csv
- National totals, daily 2020-01-01 → 2022-12-31: every C (containment), E (economic),
  H (health) and V (vaccination) indicator plus the indexes. Column names snake_cased
  (`C1M_School closing` → `c1m_school_closing`).

### World Bank — unemployment and life expectancy

- Unemployment, total (% of labour force, modelled ILO estimate), `SL.UEM.TOTL.ZS`:
  https://api.worldbank.org/v2/country/all/indicator/SL.UEM.TOTL.ZS?format=json&per_page=20000&date=2010:2025
- Life expectancy at birth (years), `SP.DYN.LE00.IN`:
  https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?format=json&per_page=20000&date=2010:2025

### Derived: `society_covid`

Per country (ISO3 code):

- `school_weeks_full` — days with OxCGRT `C1M` = 3 (closing required at all levels) in 2020–22, ÷ 7
- `school_weeks_partial_or_full` — days with `C1M` ≥ 2 (required at some or all levels), ÷ 7
- `unemployment_rise_pp` — highest unemployment rate in 2020–22 minus 2019, in %-points
- `life_expectancy_drop_years` — 2019 life expectancy minus the lowest of 2020–22

### World Bank — healthcare capacity

- Current health expenditure (% of GDP), `SH.XPD.CHEX.GD.ZS`
- Current health expenditure per capita (current US$), `SH.XPD.CHEX.PC.CD`
- Physicians (per 1,000 people), `SH.MED.PHYS.ZS`
- Nurses and midwives (per 1,000 people), `SH.MED.NUMW.P3`
- Hospital beds (per 1,000 people), `SH.MED.BEDS.ZS`

Same API pattern: `https://api.worldbank.org/v2/country/all/indicator/<code>?format=json&per_page=20000&date=2010:2025`

### Derived: `health_capacity`

Per country and indicator, the latest value in 2015–2019 (pre-COVID capacity), plus the year it is from
(`<column>_year`). Used as an explanatory factor in the app, not as a score criterion.

### IMF World Economic Outlook — no longer used

An earlier version of the app used the IMF's October 2019 growth forecast as a second "no COVID"
baseline for the GDP loss. It was dropped to keep the analysis simple: the app now uses only the
2015–19 World Bank trend, so the IMF table, download and the `imf_*` columns are gone.

Not added because coverage is too incomplete for the countries analysed: Google COVID-19
Community Mobility Reports (missing ~10%), World Bank government debt `GC.DOD.TOTL.GD.ZS`
(available for ~1 in 3 countries).

## Referenced but not loaded

| What | URL |
|---|---|
| Hong Kong CHP — deaths/cases by age × vaccine type × dose (PDF, 21 Dec 2022) | https://www.coronavirus.gov.hk/pdf/death_analysis/death_analysis_20221221.pdf |
| Hong Kong CHP — earlier editions | https://coronavirus.gov.hk/pdf/death_analysis/death_analysis_20221019.pdf, https://coronavirus.gov.hk/pdf/death_analysis/death_analysis_20220817.pdf |
| Malaysia MoH — individual death linelist with vaccine brand | https://github.com/MoH-Malaysia/covid19-public/blob/main/epidemic/linelist/linelist_deaths.csv |
| Malaysia MoH — daily doses by brand | https://github.com/MoH-Malaysia/covid19-public/blob/main/vaccination/vax_malaysia.csv |
| CDC — case/death rates by vaccination status (archived copy) | https://portal.datarescueproject.org/datasets/rates-of-covid-19-cases-or-deaths-by-age-group-and-vaccination-status/ |
| CDC MMWR — COVID-19 mortality and vaccine coverage, Hong Kong | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9020860/ |
