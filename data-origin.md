# Data origin: from raw sources to the resilience app

How the data flows into `app.py` ("Who coped best with COVID-19?"), which columns
are used, and where each value is calculated. URLs and provenance per source are in
`sources.md`.

★ = calculated (not copied from a source).

```
 ┌─────────────────────────── 1. RAW SOURCES ───────────────────────────┐
 │ owid-covid-data.csv          OWID, daily per country (local file)    │
 │ OxCGRT_compact_national_v1   Oxford policy tracker, daily (download) │
 │ worldbank-gdp.csv            World Bank API, yearly                  │
 │ worldbank-social.csv         World Bank API, yearly                  │
 │ worldbank-health.csv         World Bank API, yearly                  │
 │ imf-weo-2019-10-gdp-growth   IMF forecast Oct 2019 (via DBnomics)    │
 └──────────────────────────────────┬───────────────────────────────────┘
                                    │  python build_resilience_db.py
                                    ▼
 ┌────────────────── 2. covid-resilience.db (SQLite, 175 MB) ──────────────────┐
 │ RAW TABLES (loaded as-is, cleaned)                                     │
 │  covid_data        ◄ OWID     excess_mortality_cumulative_per_million, │
 │                               total_deaths_per_million,                │
 │                               stringency_index, icu_patients_per_mill.,│
 │                               people_fully_vaccinated_per_hundred, …   │
 │  oxcgrt_daily      ◄ OxCGRT   c1m_school_closing, …                    │
 │  gdp_annual        ◄ WB       gdp_constant_2015_usd, gdp_growth_pct    │
 │  social_annual     ◄ WB       unemployment_pct, life_expectancy_years  │
 │  health_annual     ◄ WB       health spending, physicians, nurses, beds│
 │  imf_weo_2019_forecast ◄ IMF  forecast_real_gdp_growth_pct             │
 │                                                                        │
 │ DERIVED TABLES  (★ = calculated in build_resilience_db.py)                  │
 │  gdp_covid_loss  ◄ gdp_annual + imf_weo_2019_forecast                  │
 │    ★ cum_loss_2020_2023_pct_of_trend   gdp_loss_for_country()          │
 │        trend g = (GDP2019/GDP2015)^(1/4) − 1, extended over 2020-23,   │
 │        loss = (Σ trend − Σ actual) / Σ trend                           │
 │    ★ imf_cum_loss_2020_2023_pct        imf_baseline_loss()             │
 │        GDP2019 grown with IMF forecast growth 2020-23, same loss formula│
 │    ★ gdp_years_below_2019              gdp_recovery()                  │
 │        number of years 2020-24 with GDP < 2019                         │
 │  society_covid   ◄ oxcgrt_daily + social_annual                        │
 │    ★ school_weeks_full                 school_closure_weeks()          │
 │        days with C1M = 3 in 2020-22, ÷ 7                               │
 │    ★ unemployment_rise_pp              social_changes()                │
 │        max(2020-22) − 2019                                             │
 │    ★ life_expectancy_drop_years        social_changes()                │
 │        2019 − min(2020-22)                                             │
 │  health_capacity ◄ health_annual                                       │
 │    ★ latest value 2015-2019 per indicator   health_capacity()          │
 │                                                                        │
 │ (also present, not used by the app: vaccinations_by_manufacturer,     │
 │  locations, ve_primary_series, ve_booster — for the notebook)          │
 └──────────────────────────────────┬─────────────────────────────────────┘
                                    │  python export_app_data.py
                                    │  (SQL select + filter only, no calculations)
                                    ▼
 ┌──────────────── 3. app-data/*.parquet (0.9 MB, in git) ────────────────┐
 │  daily.parquet           ◄ covid_data: 10 columns, real countries only │
 │                            (continent IS NOT NULL, UK nations dropped) │
 │  gdp_loss.parquet        ◄ gdp_covid_loss (aggregates dropped)         │
 │  society.parquet         ◄ society_covid                               │
 │  health_capacity.parquet ◄ health_capacity                             │
 └──────────────────────────────────┬─────────────────────────────────────┘
                                    │  resilience.py load_*()
                                    ▼
 ┌────────── 4. resilience.py — one row per country (★ = calculated) ─────┐
 │ country_metrics(cutoff)   from daily, up to "Deaths measured up to"    │
 │  ★ excess_pm          last cumulative excess ≤ cutoff                  │
 │                       (NaN if > 6 months old)                          │
 │  ★ reported_pm        max total_deaths_per_million                     │
 │  ★ avg_stringency     mean stringency_index 2020 → min(cutoff, 2022)   │
 │  ★ peak_icu_pm        max icu_patients_per_million                     │
 │  ★ pct_fully_vax      max people_fully_vaccinated_per_hundred          │
 │  ★ days_to_50pct_vax  first date ≥ 50% − 2020-12-08                    │
 │  ★ excess_vs_reported excess_pm / reported_pm                          │
 │   + joined on ISO code: gdp_loss, society, health_capacity columns     │
 │ with_gdp_baseline()       ★ gdp_loss_pct = IMF or trend column (sidebar)│
 │ select_peers()            filter: min population, continents, countries│
 │ score_countries()         ★ rank per criterion → 0..1, weighted → 0-100│
 │ rank_stability()          ★ ranking across all weight combinations     │
 │ capacity_correlations()   ★ correlation of capacity vs. outcomes       │
 └──────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
 ┌──────────────────────── 5. app.py (Streamlit UI) ──────────────────────┐
 │ Criteria (score) ─► column                                             │
 │   health    ─► excess_pm | reported_pm |                               │
 │                life_expectancy_drop_years   (sidebar choice)           │
 │   economy   ─► gdp_loss_pct                                            │
 │   jobs      ─► unemployment_rise_pp                                    │
 │   education ─► school_weeks_full                                       │
 │   freedom   ─► avg_stringency                                          │
 │   recovery  ─► gdp_years_below_2019                                    │
 │ Shown, not scored: peak_icu_pm, pct_fully_vax, health_capacity columns │
 │ Tabs: Criteria · Deaths vs. cost · Ranking · Weight sensitivity ·      │
 │       End date matters · Vaccination speed · Healthcare capacity ·     │
 │       Data quality · Calculations                                      │
 └────────────────────────────────────────────────────────────────────────┘
```

## Where calculations happen

1. **`build_resilience_db.py`**: fixed calculations per country and year (GDP loss, recovery
   years, school-closure weeks, unemployment rise, life-expectancy drop, healthcare
   capacity). They don't depend on anything chosen in the app.
2. **`resilience.py`**: everything that depends on the sidebar (cutoff date, GDP
   baseline, peer group, weighted score).

`export_app_data.py` calculates nothing: it only selects columns and filters out
aggregate regions.

## Refreshing the data

```bash
python build_resilience_db.py      # rebuild covid-resilience.db (--refresh re-downloads sources)
python export_app_data.py     # rewrite app-data/*.parquet for the app
```
