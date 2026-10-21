# COVID-19 Vaccine Safety & Efficacy: Data Analysis

**Question examined:** Does real-world data support or contradict the claim "COVID-19 vaccines killed more people than they helped"?

**Date of analysis:** 2026-08-24
**Files in this directory:** `owid-covid-data.csv` (raw OWID download), `country_trends_biweekly.csv` (cleaned biweekly trends for 6 countries + World), `vaccination_cfr_summary.csv` (pre/post-vaccination case-fatality-rate comparison), this report.

---

## Bottom line

**The weight of Tier 1 (peer-reviewed, causally-adjusted) evidence contradicts the claim.** No credible peer-reviewed study finds that COVID-19 vaccines caused net harm at a population level. Multiple independent peer-reviewed modelling and cohort studies estimate vaccines prevented on the order of **14–20 million deaths globally in just the first year** of rollout (2020–2021), against a documented, causally-confirmed death toll from vaccination that is in the **hundreds, not millions** worldwide (e.g., ~9 confirmed deaths from J&J-linked TTS in the US by March 2022). The one major peer-reviewed paper that purported to show large-scale excess deaths linked to vaccination — a May 2024 *BMJ Public Health* study — was **retracted in August 2026** after an institutional investigation found its causal claims did not reflect scientific consensus and constituted "misinformation."

This is not a novel finding — it corroborates the existing consensus among WHO, CDC, EMA, and independent academic researchers, reached through years of post-market surveillance across many countries. Real, documented, narrower harms exist (below) and should not be minimized — but they do not add up to net harm.

---

## 1. OWID case/death/vaccination data (Tier 1)

**Source:** Our World in Data COVID-19 dataset (github.com/owid/covid-19-data), which aggregates WHO, Johns Hopkins, and national government reporting. Downloaded in full (429,436 rows, ~98MB) on 2026-08-24. Note: OWID/WHO stopped daily case/death updates in mid-2024; cumulative figures below reflect the last reported values (as of 2024-08-04).

### Case Fatality Rate (CFR) before vs. after each country crossed 10% full vaccination

CFR here = 7-day-smoothed new deaths ÷ 7-day-smoothed new cases, averaged over each period. This is a **descriptive/observational comparison, not a causal estimate** — see caveats below.

| Country | Reached 10% fully vax | CFR before (%) | CFR after (%) | Relative change | Cumulative deaths/million (as of 2024-08-04) | Peak fully vaccinated (%) |
|---|---|---|---|---|---|---|
| United States | 2021-03-04 | 1.83 | 0.81 | **-55.6%** | 3,494 | 69.5% |
| United Kingdom | 2021-04-09 | 3.43 | 0.39 | **-88.7%** | 3,404 | 75.2% |
| Israel | 2021-01-22 | 0.74 | 0.20 | **-72.7%** | 1,396 | 65.2% |
| Germany | 2021-05-11 | 2.62 | 0.24 | **-90.8%** | 2,081 | 76.2% |
| Japan | 2021-06-22 | 1.82 | 0.18 | **-89.9%** | 598 | 83.4% |
| Brazil | 2021-05-26 | 2.79 | 1.20 | **-56.9%** | 3,339 | 81.8% |
| World | 2021-07-18 | 2.18 | 0.51 | **-76.8%** | 883 | 64.9% |

**Pattern:** In every country examined, measured case-fatality rate fell sharply (56–91% relative decline) after vaccination campaigns reached meaningful coverage. This is directionally consistent with vaccines reducing death risk, and matches the causal cohort literature (below).

**Important caveats on this table (why it's suggestive, not proof, on its own):**
- **Confounded by time**: the same period saw the emergence of Omicron (intrinsically less severe per infection than Delta/ancestral strains), major treatment improvements (dexamethasone, Paxlovid, better ICU protocols), and widespread prior infection-acquired immunity — all of which independently lower CFR regardless of vaccination.
- **Testing-denominator drift**: as home testing became common, official case counts increasingly undercounted mild/asymptomatic infections, artificially inflating apparent CFR in the "before" period relative to "after," which if anything means this table may understate the true improvement or partly reflect a testing artifact rather than a pure vaccine effect.
- This is why the causal question ("did vaccines net save lives") is answered by Tier 1 cohort/modelling studies below, not by this raw trend line — the table is included per the task brief as context, not as the causal proof.

---

## 2. Peer-reviewed lives-saved modelling (Tier 1)

**Watson, O.J. et al., "Global impact of the first year of COVID-19 vaccination: a mathematical modelling study," *The Lancet Infectious Diseases*, June 2022.**
- Estimated **14.4 million deaths averted** (95% credible interval 13.7–15.9 million) across 185 countries/territories between 8 Dec 2020 and 8 Dec 2021, based on official reported COVID-19 deaths.
- Using excess-mortality-based estimates instead of official counts (to correct for undercounting), the same model estimated **19.8 million of a possible 31.4 million deaths averted** — the widely cited "~20 million lives saved in year one" figure.
- Published in a top-tier peer-reviewed journal (Lancet Infectious Diseases); Imperial College London-led modelling consortium (same group that produces widely-used WHO/UK pandemic models).

**Follow-on study: "Estimated number of lives directly saved by COVID-19 vaccination programmes in the WHO European Region from December 2020 to March 2023,"** *The Lancet Regional Health – Europe* (2024) — a retrospective surveillance study (not just modelling) extending the finding to the WHO European Region across the full early pandemic period, corroborating large-scale lives-saved estimates using actual regional surveillance data rather than pure simulation.

### Credible peer-reviewed studies claiming net harm from vaccination

**None found.** This was searched for directly and explicitly, per the task instructions, rather than assuming false balance. What was found instead:

- **The one major paper that made this claim in a peer-reviewed venue — "Serious harms of the COVID-19 vaccines" (medRxiv preprint) and a related paper published in *BMJ Public Health* (May 2024)** claiming >3 million excess deaths in 47 Western countries attributable in part to vaccination — **was retracted by BMJ Group in August 2026.** The retraction notice, per an institutional investigation, found the paper's "discussion of causes of mortality is imbalanced, lacks rigour, and includes misinformation," and that the authors' conclusions were "misleading, selective, and disproportionately focused on the negative effects of vaccination" in a way that did not reflect scientific consensus at the time. Two of four authors and the host institution supported the retraction; the corresponding author disputed it. (Reported by Retraction Watch, Scientific American, The Scientist, CIDRAP — Aug 2026.)
- A large **28-million-adult long-term vaccine safety cohort study** found "a causal link between mRNA vaccination and excess long-term mortality appears highly unlikely," with vaccinated individuals showing equal or lower death rates across cancer, heart disease, and accidental-injury categories.
- A 2026 case-control study found no evidence mRNA vaccines increased sudden cardiac death in young, healthy adults.

**Conclusion on this point:** the peer-reviewed literature is not "mixed" or "50/50" on net population-level harm — it is close to unanimous that vaccines produced large net benefit, and the one prominent contrary paper failed peer scrutiny after publication and was formally withdrawn.

---

## 3. VAERS raw data (Tier 2 — NOT causal, mandatory caveat)

**Source:** VAERS (Vaccine Adverse Event Reporting System), jointly run by CDC/FDA, vaers.hhs.gov.

- **Reported deaths following any COVID-19 vaccination, as of Nov 2, 2024: approximately 14,506** (cumulative, all reports since vaccines launched in Dec 2020, out of roughly 13+ billion doses administered worldwide / ~676 million doses administered in the US alone).

**MANDATORY CAVEAT (per CDC/FDA, stated every time this number is cited):**
> VAERS is a **passive surveillance system**. Anyone — patients, family members, healthcare providers — can submit a report. **A report to VAERS does not mean the vaccine caused the event, only that the event occurred at some point after vaccination.** Reports may be incomplete, inaccurate, unverified, or purely coincidental. Providers are legally required to report *any* death after vaccination regardless of cause — including, per CDC's own example, someone who drowned or was struck by lightning after being vaccinated. CDC/FDA explicitly state that a review of available clinical information (death certificates, autopsy, medical records) has **not established a causal link** to vaccination for the overwhelming majority of these reports.

**What has actually been confirmed causal**, via active follow-up investigation (contrast with the 14,506 raw reports above):
- **Thrombosis with Thrombocytopenia Syndrome (TTS)** linked to the J&J/Janssen vaccine: ~4 cases per million doses; through March 2022, FDA confirmed 60 TTS cases with **9 deaths** in the US.
- **Anaphylaxis**: ~2–5 cases per million doses, rarely fatal, treatable.
- **Myocarditis/pericarditis** (see below): a confirmed but very rarely fatal risk, concentrated in young males after mRNA vaccination.

**Side-by-side scale comparison:**

| Metric | Trust tier | Value | Causal? |
|---|---|---|---|
| VAERS raw reported deaths (any cause, any time after any COVID vaccine, cumulative through Nov 2024) | Tier 2 | ~14,506 | **No** — passive, unverified, includes coincidental deaths |
| Confirmed causal deaths from TTS (J&J, US, through Mar 2022) | Tier 1 (investigated) | 9 | Yes |
| Lives saved, global, year 1 of rollout (Lancet/Watson et al. 2022, excess-mortality basis) | Tier 1 | ~19.8 million | Yes (modelled, causally-adjusted) |

Even taking the raw, uninvestigated VAERS death-report count at full face value with zero adjustment for coincidental deaths (which the CDC explicitly says not to do), it is roughly **three orders of magnitude smaller** than the peer-reviewed lives-saved estimate. The comparison is not close.

---

## 4. Real, well-documented narrower harms (Tier 1 — not glossed over)

The honest picture includes genuine, confirmed adverse effects — these are real and are exactly why post-market surveillance systems like VAERS exist and are valuable for signal detection, even though raw counts can't establish causation on their own:

- **Myocarditis/pericarditis after mRNA vaccination, concentrated in young males:** CDC-estimated rates after the second dose of mRNA vaccine reach **~66.7 per million in males 12–17**, with age/sex-stratified rates around 42.6 per million (boys 12–15) and 71.5 per million (boys 16–17), versus ~4–8 per million in same-age females. This is a confirmed, causally-established signal (not just a VAERS report count) — it emerged from active surveillance and was significant enough that some countries (e.g., several Nordic countries, and briefly others) adjusted dosing recommendations for young males. Importantly, most cases were mild and self-resolving, and several studies found the myocarditis risk from **COVID-19 infection itself** was comparable or higher in some age bands (e.g., ~30 cases per million from infection in the general population, higher in older males) — meaning vaccination did not necessarily increase net myocarditis risk relative to the disease it prevents, though the comparison is age- and sex-dependent and not uniformly favorable in every subgroup.
- **TTS (blood clots with low platelets) after J&J/AstraZeneca (adenovirus-vector vaccines):** a confirmed rare but serious harm, ~4 per million doses for J&J, leading several countries to restrict or withdraw use of adenovirus-vector vaccines in certain age groups. This is the clearest case of a vaccine-specific harm signal that changed real-world policy.
- **Anaphylaxis:** rare (2–5 per million) and treatable, but real and immediate.

None of these confirmed harms, even summed, approach a scale that would flip the net calculus at a population level — but they are legitimate, peer-reviewed, causally-supported findings, and any honest analysis should state them plainly rather than either exaggerating or erasing them.

---

## 5. Trust-tier summary of every figure cited above

| Figure | Tier | Source |
|---|---|---|
| CFR before/after vaccination by country | 1 | OWID aggregation of WHO/JHU/national gov data (this analysis) |
| 14.4M / 19.8M lives saved, year 1 | 1 | Watson et al. 2022, *Lancet Infectious Diseases* (peer-reviewed) |
| WHO European Region lives-saved follow-up | 1 | *Lancet Regional Health – Europe*, 2024 (peer-reviewed) |
| 28M-adult mortality safety cohort | 1 | Peer-reviewed long-term safety study (per Gavi/vaccines work summary) |
| BMJ Public Health retraction | 1 (meta) | BMJ Group official retraction notice, Aug 2026; Retraction Watch, Scientific American |
| Myocarditis rates per million | 1 | CDC surveillance data, peer-reviewed (Circulation, *AHA Journals*) |
| TTS: 9 confirmed deaths, ~4/million | 1 (confirmed via investigation) | FDA safety surveillance |
| VAERS: ~14,506 reported deaths | 2 | VAERS public data, vaers.hhs.gov — **passive, unverified, non-causal** |

---

## 6. This is corroboration, not new ground

This analysis independently reproduces conclusions that have already been reached, through years of post-market surveillance and independent research, by the WHO, US CDC, US FDA, European Medicines Agency (EMA), and equivalent national health bodies in essentially every country with a functioning vaccination program — all of which continue to recommend COVID-19 vaccination based on their respective ongoing safety monitoring. The retraction of the one major contrary peer-reviewed paper by its own publisher, after independent institutional review, is itself part of that same self-correcting scientific consensus process, not a departure from it.

## Genuine open questions that remain

- Precise long-term (5–10+ year) safety data is still accumulating for a technology (mRNA platforms) that is relatively young in mass deployment, though several years of follow-up so far show no emerging late-onset signal.
- Optimal dosing/spacing to minimize myocarditis risk in young males specifically continues to be refined and varies by country guideline.
- Bivalent/updated-strain booster effectiveness estimates carry wider uncertainty than the original 2021 rollout studies, since RCT-grade evidence is harder to generate for each new variant-adapted formulation.

These are legitimate areas of ongoing scientific refinement — they are not evidence for the "net harm" claim, which the peer-reviewed literature does not support.
