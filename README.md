# COVID-19 Vaccine Efficacy & Safety Data (OWID + Primary Sources)

A trust-tiered dataset for investigating COVID-19 vaccine efficacy and safety with
real, citable primary sources — built to let the data answer the question rather than
assume a conclusion. Every claim in `primary_sources.json` is tagged with a trust tier
(peer-reviewed causal evidence vs. official-but-non-causal passive surveillance data)
and a real DOI/URL.

## Files

- **owid-covid-data.csv** — 429,436 rows. Full raw Our World in Data COVID-19 dataset
  (cases, deaths, vaccination rates, testing, by country and date). Source:
  [github.com/owid/covid-19-data](https://github.com/owid/covid-19-data).

- **country_trends_biweekly.csv** — Biweekly case/death/vaccination trend series for
  US, UK, Israel, Germany, Japan, Brazil, and World, derived from the OWID dataset.

- **vaccination_cfr_summary.csv** — Case-fatality-rate comparison for each of those
  seven locations, before vs. after crossing 10% full vaccination coverage.

- **vaccinations-by-manufacturer.csv** — 68,510 rows. Cumulative doses administered per
  vaccine brand (Pfizer/BioNTech, Moderna, Oxford/AstraZeneca, Johnson&Johnson, and 11
  others), per location, per day. Covers ~44 mostly-European locations (plus the US,
  Canada, Japan, South Korea, and a few others), 2020-12 to 2024-08 — a different,
  smaller set of locations than the main OWID dataset. Source:
  [github.com/owid/covid-19-data](https://github.com/owid/covid-19-data).

- **primary_sources.json** — Machine-readable citation registry. Each entry:
  `claim, source_title, authors, journal, year, doi_or_url, trust_tier, exact_quote_or_stat, notes`.
  Covers the Lancet Infectious Diseases lives-saved model (Watson et al. 2022), four
  independent real-world cohort studies (Israel, UK, Norway, France), myocarditis/TTS
  safety-signal studies (CDC, Nordic 23M-person cohort, 99M-person GVDN cohort), the
  official VAERS non-causality language (quoted verbatim from vaers.hhs.gov), a
  retracted paper that once claimed net harm (with the actual retraction notice), and
  the strongest genuine peer-reviewed counter-evidence found in an active search
  (Fraiman et al. 2022) — included with its published methodological critiques rather
  than omitted or accepted uncritically.

- **primary_sources_notes.md** — Human-readable narrative version of the same registry.

- **covid_vaccine_analysis_summary.md** — Earlier-stage summary report (superseded by
  the companion notebook, kept for the intermediate analysis trail).

## Companion notebook

`covid_vaccine_data_investigation.ipynb` (published as a linked Kaggle Notebook) loads
these files and walks through: the lives-saved model, four real-world cohort
comparisons, OWID case-fatality-rate trend charts, the VAERS passive-surveillance
caveat with verbatim official quotes, myocarditis/TTS rates from independent
surveillance systems, the retracted paper's actual retraction reasoning, and the
strongest real counter-evidence found — ending in a trust-tiered bottom-line table.

## Trust tiers used throughout

- **Tier 1** — peer-reviewed, either a causal modelling study or a large matched/cohort
  observational study, or an official retraction/primary-source document fetched directly.
- **Tier 2** — official government passive-surveillance data (e.g. VAERS) — real, but
  explicitly *not* causal by the data owner's own documentation; anyone can file a
  report and it is not verified before publication.
- **Tier 3** — preprints / non-peer-reviewed sources, included only where the notebook
  documents that it searched for and evaluated a specific claim, not as evidence.

## Caveats

- The OWID case-fatality-rate before/after comparison is population-level, not
  individually matched, and is confounded by variant-severity shifts (e.g. Omicron)
  and treatment improvements occurring in the same window — it's supporting context,
  not standalone causal proof.
- Several observational cohort studies in `primary_sources.json` flag their own
  "healthy vaccinee bias" limitation (people who choose vaccination may differ
  systematically from those who don't, independent of vaccine effect) — this is
  preserved in the `notes` field rather than smoothed over.
- Where a citation could not be independently re-verified with an exact DOI in the
  time available, it is explicitly flagged `UNVERIFIED` in the `trust_tier` or `notes`
  field rather than presented as confirmed.

All data retrieved 2026-08-24.
