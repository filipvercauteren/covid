# Primary Source Research Notes — COVID-19 Vaccine Safety/Efficacy Deepening Pass

**Purpose:** Deepen the existing `covid_vaccine_analysis_summary.md` with verified primary-source citations (DOI/PMID/URL), per the six-item research brief. This file gives narrative detail per source; `primary_sources.json` has the same material in structured form for programmatic use in the notebook.

**Method:** WebSearch + WebFetch only, this session. Where a number could not be independently confirmed against a primary source (only found via secondary aggregation, or a page could not be fetched — several PubMed/BMJ/ScienceDirect pages returned cookie-consent stubs or 403s rather than content), this is flagged explicitly below and in the JSON `notes` field rather than presented as verified.

---

## 1. Watson et al. 2022 — Lancet Infectious Diseases modelling paper

**Full citation:** Watson OJ, Barnsley G, Toor J, Hogan AB, Winskill P, Ghani AC. "Global impact of the first year of COVID-19 vaccination: a mathematical modelling study." *Lancet Infect Dis.* 2022;22(9):1293-1302. DOI: [10.1016/S1473-3099(22)00320-6](https://doi.org/10.1016/S1473-3099(22)00320-6). PMC9225255. PMID 35753318.

Confirmed directly from the paper's PMC record and corroborating Imperial College London press materials:

- **Two headline estimates**, both for 185 countries/territories, 8 Dec 2020 – 8 Dec 2021:
  - **14.4 million deaths averted**, fitting the model to *officially reported* COVID-19 deaths.
  - **19.8 million deaths averted** (of a possible 31.4 million), fitting the model to *excess-mortality*-based death estimates instead — this correction for undercounting is why this is the more commonly cited "~20 million" figure.
- **Mechanism split:** 79% (15.5M) of averted deaths from direct vaccine protection; 21% (4.3M) from indirect effects (reduced transmission, reduced healthcare-system strain).
- **Regional:** ~7.5 million deaths averted in COVAX-covered countries specifically. Imperial's press release separately states that meeting COVAX's 20% coverage target would have averted an additional 81,750 deaths, and meeting WHO's 40% target would have averted an additional 599,300 lives — these are stated as additional counterfactual scenarios, not part of the core 14.4M/19.8M figures.
- **China was excluded** from the whole analysis "due to its unique position as the origin of the detected epidemic and its large influence on estimates" — this is the authors' own stated scope limitation, not an external critique.

**Its own methodological framing (the key ask of item 1):** This is explicitly a **counterfactual mathematical model** — it compares the pandemic's actual trajectory against a simulated scenario in which no vaccine had been delivered, using disease-transmission and vaccine-efficacy modelling (the same modelling group produces widely-used WHO/UK pandemic models). It is **not** a direct headcount of individuals whose deaths were causally traced to vaccination — the paper does not and cannot claim that. This distinction matters and should be preserved verbatim in the notebook rather than softened into "vaccines saved 20 million lives" as a flat empirical fact.

A **correction notice** exists for this paper (Lancet Infect Dis, DOI PIIS1473-3099(23)00566-2) — I located its existence but did not pull its content this pass. Recommend checking it before quoting exact figures in the final notebook, in case any headline number was revised.

**A counter-critique exists but fails the credibility bar:** Denis Rancourt and Joseph Hickey published a preprint (Authorea, not peer-reviewed) arguing the Watson model's assumptions are "highly improbable" and produce results with "no connection to actual mortality." See item 6 below for why this was not treated as credible counter-evidence.

**Item flagged as NOT independently reverified this pass:** the prior summary also cites a follow-on *Lancet Regional Health – Europe* (2024) surveillance-based study extending the finding to the WHO European Region. I was not able to re-confirm its exact DOI/title/authors/numbers in this session — this should be pulled directly before the notebook cites it as a distinct, real source.

---

## 2. The retracted BMJ Public Health paper (Mostert et al.)

**Full citation of the original (now-retracted) paper:** Mostert S, Hoogland M, Huibers M, Kaspers G. "Excess mortality across countries in the Western World since the COVID-19 pandemic: 'Our World in Data' estimates of January 2020 to December 2022." *BMJ Public Health.* 2024;2:e000282. DOI: [10.1136/bmjph-2023-000282](https://doi.org/10.1136/bmjph-2023-000282) — this DOI now resolves with a "RETRACTED:" prefix on the title.

**Exact headline number:** the paper reported **3,098,456 total excess deaths** across 47 Western-world countries, 1 Jan 2020 – 31 Dec 2022 (broken down as 1,033,122 in 2020; 1,256,942 in 2021; 808,392 in 2022). The prior summary's ">3 million" is directionally correct but the notebook should use the precise figure.

**Timeline, reconstructed from multiple sources:**
1. **6 May 2024** — original publication.
2. **June 2024** — demographer Ariel Karlinsky raised concerns and requested retraction; BMJ issued an **Expression of Concern** (DOI `10.1136/bmjph-2023-000282eoc`, dated 14 June 2024). This EoC is itself an important primary source: it states plainly that the paper's authors **"looked only at trends in excess mortality over time, not its causes,"** and that the study **"does not support the claim that vaccines are a major contributory factor to excess deaths since the start of the pandemic."** In other words, even before the retraction, BMJ's own editorial position was that the paper never actually supported the vaccine-causation narrative that was built on top of it in public discourse — the retraction ultimately concerned how the paper's *own discussion section* framed causes, not merely how outsiders misused it.
3. **3 June 2026** — corresponding author Saskia Mostert testified before a U.S. Senate subcommittee, defending the paper.
4. **11 August 2026** — retraction notice published (~2 months after the Senate testimony).

**Investigation and exact retraction rationale:** conducted by the **Princess Máxima Center for Pediatric Oncology** (Netherlands), the institution of three of the four authors (Mostert was reportedly unavailable to participate in her institution's review per one source). The retraction notice's stated reason, quoted directly: **"misinformation in the discussion regarding the possible causes of excess mortality, and because the limited nature of the original work by the authors was not sufficiently described."** A CIDRAP commentary on the episode adds more specific texture: the investigating committee found the paper gave disproportionate attention to vaccines and containment measures as *possible causes* of excess mortality, while giving too little attention to other explanations, and that it selectively cited supporting research while omitting contrary evidence — e.g., quoting one source's claim of "1 to 2 severe adverse events per 1,000 vaccinees" while not engaging with the 23-million-person Nordic cohort study (see item 4) that found much lower rates and no deaths from vaccine-linked myocarditis/pericarditis; misquoting a source on autoimmunity risk in a way that reversed its actual conclusion; and citing a global (not Western-specific) infection-fatality-rate figure that understated pandemic severity in the Western countries actually being studied.

**Important nuance for the notebook:** the investigating committee explicitly **did not find scientific misconduct or malicious intent** — it attributed the problems to "carelessness, gaps in knowledge, and negligence." This should not be flattened into "the authors were caught faking data" — it was a *causal-inference and balance-of-evidence* problem in the discussion section, not (per the investigation) fabrication.

**Author positions:** co-authors Kaspers and Huibers supported the retraction ("concerns about misinterpretation"); corresponding author Mostert and co-author Hoogland disagreed with it.

---

## 3. Additional peer-reviewed observational/cohort studies (vaccinated vs. unvaccinated, real cohorts)

Four were located and confirmed, spanning Israel, the UK, Norway, and France — a broader and more geographically diverse set than the prior summary's vague "28-million-adult... per Gavi summary" reference:

### Israel — Clalit Health Services (Dagan, Barda, Balicer et al.)
Dagan N, Barda N, Kepten E, et al. "BNT162b2 mRNA Covid-19 Vaccine in a Nationwide Mass Vaccination Setting." *N Engl J Med.* 2021;384:1412-1423. DOI: [10.1056/NEJMoa2101765](https://doi.org/10.1056/NEJMoa2101765).
- Matched cohort, 596,618 vaccinated vs. 596,618 unvaccinated (1:1 propensity matching), from Clalit (covers ~52% of the Israeli population).
- **Vaccine effectiveness against death: 72% (95% CI 19–100)** at days 14–20 post first dose. Note the wide confidence interval — this early-follow-up estimate has real statistical uncertainty at the upper/lower bound, which should be shown alongside the point estimate.
- A related, not-independently-reverified-this-pass Clalit booster study (NEJM 2021;385:1393) reportedly found an adjusted hazard ratio of 0.10 (95% CI 0.07–0.14) for COVID-19 death in a booster vs. non-booster group — flagged for direct confirmation before use.

### UK — OpenSAFELY platform
"Changes in COVID-19-related mortality across key demographic and clinical subgroups... using the OpenSAFELY platform on 18 million adults in England." medRxiv preprint 10.1101/2022.07.30.22278161, with a journal version apparently published in Lancet Public Health (exact journal DOI not independently re-confirmed this pass — the ScienceDirect page returned a 403 and could not be fetched directly).
- ~18.7–18.8 million adults, 3 pandemic waves.
- Crude COVID-19 death rate per 1,000 person-years: 4.48 (wave 1) → 2.70 (wave 2) → 0.64 (wave 3).
- Groups prioritized for early vaccination (80+, neurological disease, learning disability, severe mental illness) saw 90–91% declines wave-1-to-wave-3; immunosuppressed/transplant/CKD/hematologic-malignancy groups saw only 0–25% declines.
- **Caveat:** this is a before/after comparison across pandemic waves, not a same-period vaccinated-vs-unvaccinated match — it carries the same variant-severity/treatment-improvement confounds already flagged in the base OWID CFR table. Still a genuine large-N UK real-world data point.

### Norway — nationwide registry (Dahl, Tapia, Bøås, Bakken, Gulseth)
"COVID-19 mRNA vaccination and all-cause mortality in the adult population in Norway during 2021–2023: a population-based cohort study." *BMJ Public Health*, published 5 Feb 2026. DOI: [10.1136/bmjph-2024-001859](https://doi.org/10.1136/bmjph-2024-001859). PMID 41658231.
- N = 4,645,910 adults, 132,963 deaths.
- All-cause mortality rate per 100,000 person-years, fully-vaccinated vs. unvaccinated: **ages 18–44: 51.5 vs. 73.6; ages 45–64: 295.1 vs. 405.3; ages 65+: 3,620.2 vs. 4,783.8** — lower in every age band for the vaccinated group.
- Authors explicitly flag **"healthy vaccinee bias"** as an inherent limitation, and name low socioeconomic status as the "main unknown confounding factor" — i.e., the people who get vaccinated may simply be systematically healthier or more engaged with healthcare, independent of any vaccine effect, and this study cannot fully rule that out. This caveat should travel with the number.

### France — national claims database (Semenzato, Zureik et al.)
"COVID-19 mRNA Vaccination and 4-Year All-Cause Mortality Among Adults Aged 18 to 59 Years in France." *JAMA Network Open*, published 4 Dec 2025. DOI: [10.1001/jamanetworkopen.2025.46822](https://doi.org/10.1001/jamanetworkopen.2025.46822). PMID 41343214.
- **22,767,546 vaccinated + 5,932,443 unvaccinated ≈ 28.7 million total** — this almost certainly is the actual source of the prior summary's uncited "28-million-adult... cohort study" claim, which had previously been attributed only vaguely to "per Gavi/vaccines work summary." **Recommend replacing that vague citation with this real one.**
- Median follow-up 45 months. Deaths: 98,429 (0.4%) vaccinated vs. 32,662 (0.6%) unvaccinated.
- Weighted HR for all-cause mortality: **0.75 (95% CI 0.75–0.76)** — 25% lower in vaccinated. COVID-specific mortality wHR 0.26 (95% CI 0.22–0.30) — 74% lower.
- Authors' own quote, verified directly: **"a causal link between mRNA vaccination and excess long-term mortality appears highly unlikely."**
- Stated limitations (authors' own): ~300,000 fraudulent health passes issued in France in 2022 could cause vaccination-status misclassification; cause-of-death data available for only 59% of deaths; possible residual confounding from vaccine hesitancy and socioeconomic factors; possible healthy-vaccinee/frailty bias despite statistical weighting.

---

## 4. Myocarditis and TTS per-million risk figures

### Myocarditis (mRNA vaccines, young males) — CDC/JAMA
The likely underlying source for the "42.6 / 71.5 per million" and "~66.7 per million" figures used in the prior summary is **Oster ME, Shay DK, Su JR, et al., "Myocarditis Cases Reported After mRNA-Based COVID-19 Vaccination in the US From December 2020 to August 2021," JAMA, 2022** — reporting rates of **42.6 per million (boys 12–15)** and **71.5 per million (boys 16–17)** within 7 days of the second mRNA dose.

**Flag: I was not able to independently pull the JAMA abstract directly this pass** (PubMed returned a cookie-consent stub rather than content when fetched). These numbers are carried forward via secondary-source aggregation, consistent with the numbers already in the prior summary, but the exact DOI, full confidence intervals, and any subsequent corrections should be pulled directly from JAMA before treating this as fully hand-verified in the final notebook.

### Myocarditis — independent Nordic confirmation (23.1 million people)
Karlstad O, Hovi P, Husby A, et al. "SARS-CoV-2 Vaccination and Myocarditis in a Nordic Cohort Study of 23 Million Residents." *JAMA Cardiology*, 2022. DOI: [10.1001/jamacardio.2022.0583](https://doi.org/10.1001/jamacardio.2022.0583).
- Denmark, Finland, Norway, Sweden combined, 27 Dec 2020 – 5 Oct 2021.
- **Excess myocarditis/pericarditis events within 28 days of vaccination: 4–7 per 100,000 for BNT162b2 (Pfizer); 9–28 per 100,000 for mRNA-1273 (Moderna).** Converting to per-million for comparability: **40–70 per million (Pfizer)** and **90–280 per million (Moderna)**.
- **Important unit/framing reconciliation for the notebook:** the Nordic study's Moderna figure (90–280 per million, all-vaccinee excess rate) is notably *higher* than the "~67–72 per million" figure the prior summary used — but that prior figure was specifically the CDC's Pfizer-only, age/sex-stratified *incidence* rate in teenage boys, which is a different statistic (age/sex-stratified incidence within a known high-risk subgroup) than an all-vaccinee, all-age "excess events above background" rate. Both are legitimate, real, peer-reviewed numbers — they should not be blended into one figure without explaining which is which.
- Risk highest in younger men, more pronounced after dose 2, in both national studies — an internally consistent pattern across two independent surveillance systems (US CDC and four Nordic countries), which strengthens confidence in the underlying signal even though the exact point-estimates differ by brand/method.

### TTS (adenovirus-vector vaccines) — CDC/FDA case series
See I, Su JR, Lale A, et al. "Case Series of Thrombosis With Thrombocytopenia Syndrome After COVID-19 Vaccination — United States, December 2020 to August 2021." *Annals of Internal Medicine*, 2021. DOI: [10.7326/M21-4502](https://doi.org/10.7326/M21-4502).
- **TTS reporting rate: 3.83 per million doses (J&J/Ad26.COV2.S) vs. 0.00855 per million doses (mRNA vaccines)** — several hundredfold difference, consistent with why adenovirus-vector vaccines specifically were restricted/withdrawn in several countries.
- Highest-risk subgroup: women aged 30–39 (10.6 per million) and 40–49 (9.02 per million).
- Separately, an **FDA memorandum** (Janssen TTS Review, fda.gov/media/155670) determined an overall TTS reporting rate of **3.23 per million doses** and a **TTS-associated death reporting rate of 0.48 per million doses**. Applied to the roughly 18–19 million J&J doses given in the US, this is consistent in order of magnitude with the "9 confirmed deaths through March 2022" figure already in the prior summary.
- FDA's 5 May 2022 EUA restriction of the J&J vaccine (to adults unable to receive any other vaccine) explicitly cited the >3-per-million rate.

### Largest single myocarditis/TTS confirmation source found: GVDN (99 million people)
Faksova K, Walsh D, Jiang Y, et al. "COVID-19 vaccines and adverse events of special interest: A multinational Global Vaccine Data Network (GVDN) cohort study of 99 million vaccinated individuals." *Vaccine*, 2024;42(9):2200-2211. DOI: [10.1016/j.vaccine.2024.01.100](https://doi.org/10.1016/j.vaccine.2024.01.100).
- 99 million vaccinated people, 23+ million person-years, 10 sites across 8 countries — the largest vaccine-safety dataset found in this entire search.
- Confirmed the same known signals via observed-vs-expected analysis: myocarditis after doses 1–3 of BNT162b2/mRNA-1273; pericarditis after dose 1/4 of mRNA-1273 and dose 3 of ChAdOx1; Guillain-Barré syndrome and cerebral venous sinus thrombosis after adenovirus-vector vaccines.
- **Flag:** I confirmed the qualitative signal-confirmation finding but could **not** pull the exact observed-to-expected ratios or per-million rates from the full-text tables this pass (ScienceDirect returned a 403 Forbidden on direct fetch). Recommend pulling the actual Vaccine-journal tables or the GVDN's public dashboard before quoting precise ratios from this study.

---

## 5. VAERS official caveat — verbatim quote obtained

Directly fetched from **vaers.hhs.gov/faq.html** (official government site, jointly run by CDC/FDA) this pass. Full verbatim quotes, safe to block-quote directly in the notebook:

> "Just because an adverse event happened after a person received a vaccine does not mean the vaccine caused the adverse event."

> "Some adverse events might be caused by vaccination and others might be coincidental and not related to vaccination."

> "VAERS is not designed to detect if a vaccine caused an adverse event, but it can identify unusual or unexpected patterns of reporting that might indicate possible safety problems requiring a closer look."

> "It is generally not possible to find out from VAERS data if a vaccine caused the adverse event."

> "VAERS accepts all reports of adverse health events following vaccinations without judging whether the vaccine caused the adverse health event."

> "Overall, a causal relationship cannot be established using information from VAERS report alone."

> "Reports submitted to VAERS often lack details and sometimes contains errors."

This directly and verifiably sources the caveat that was already present (but only paraphrased) in the prior summary.

---

## 6. Search for credible counter-evidence (peer-reviewed, non-retracted, non-preprint-only, non-predatory-journal studies claiming net harm)

This was searched for actively and directly, as instructed, rather than assumed away. Results:

### Found and included as genuine, credible counter-evidence:
**Fraiman J, Erviti J, Jones M, Greenland S, Whelan P, Kaplan RM, Doshi P. "Serious adverse events of special interest following mRNA COVID-19 vaccination in randomized trials in adults." *Vaccine*, 2022;40(40):5798-5805.** DOI: [10.1016/j.vaccine.2022.08.036](https://doi.org/10.1016/j.vaccine.2022.08.036). PMID 36055877.

This is a real, peer-reviewed, published, **not retracted** paper in a mainstream Elsevier journal (Vaccine) — it meets the task's credibility bar and should be included. It is a secondary reanalysis of the Pfizer and Moderna phase III placebo-controlled RCT data (not a real-world cohort — an RCT reanalysis), using an adapted Brighton Collaboration list of "adverse events of special interest." It found an **excess risk of serious adverse events of special interest of 10.1 per 10,000 vaccinated (Pfizer) and 15.1 per 10,000 vaccinated (Moderna)** relative to placebo-arm baseline rates of 17.6 and 42.2 per 10,000 respectively — i.e., these are the vaccine-minus-placebo differences.

**In fairness, this paper has received substantive, specific published methodological criticism** (from Science-Based Medicine, a science-communication outlet — not itself a peer-reviewed journal, so this critique is not "Tier 1" either, but its specific technical points are checkable): critics argue the paper (a) compared *total counts of adverse events* rather than *counts of affected participants*, which inflates the vaccine-arm total when one person has multiple related events counted separately; (b) applied inconsistent event-inclusion criteria (e.g., diarrhea counted but vomiting excluded, hyperglycemia counted but hypoglycemia excluded); (c) compared adverse-event rates directly against COVID-19 hospitalization rates, which critics call a mismatched, non-comparable metric. The journal Vaccine reportedly published two critical commentaries about the paper (2023, 2024); the original authors reportedly submitted a response letter in January 2025 that was rejected without peer review by the editor-in-chief (per secondary reporting on this — not independently verified against the original correspondence).

**Recommendation for the notebook:** present this paper honestly as real, peer-reviewed, non-retracted counter-evidence of excess serious-AE risk *in RCT data* (not a net-population-mortality-harm claim) — and pair it explicitly with the specific, checkable methodological objections raised against it, rather than either suppressing it or presenting it uncritically.

### Found and explicitly rejected as not meeting the credibility bar:
**Rancourt DG, Hickey J. "Quantitative evaluation of whether the Nobel-Prize-winning COVID-19 vaccine actually saved millions of lives."** Preprint, Authorea (not peer-reviewed), 2024.

This is the critique of the Watson et al. Lancet paper referenced in item 1. It was actively searched for as potential counter-evidence and does **not** meet the task's bar: it is preprint-only (Authorea, not a peer-reviewed journal), and lead author Denis Rancourt — a former physics professor with no epidemiology/biostatistics credentials — has a documented public track record of widely fact-checked and debunked pandemic claims (including that mask-wearing does not work against COVID-19, and that "there was no pandemic"). Multiple independent fact-checkers (FactCheck.org, PolitiFact, Science Feedback) have specifically criticized his associated ~17-million-vaccine-deaths claim for assuming, without adequate justification, that all-cause mortality spikes during the pandemic were caused by vaccination rather than by COVID-19 infection surges or reduced healthcare access. Documented here in full per the task's explicit instruction to report a genuine search, even where the source found does not qualify.

### Net conclusion on item 6:
After an actively conducted search (multiple distinct query strategies covering "net harm," "excess mortality," specific known contrarian researchers, and general "credible peer-reviewed vaccine harm" searches), **no credible peer-reviewed, non-retracted, non-preprint-only study asserting *net population-level harm* from COVID-19 vaccination was found**, beyond the now-retracted Mostert et al. paper and the non-peer-reviewed Rancourt/Hickey preprint. The one genuine, peer-reviewed, non-retracted paper reporting an adverse signal — Fraiman et al. 2022 — reports an excess of serious adverse events in RCT arms, not a net-mortality-harm finding, and carries specific, substantive published methodological criticism, which is documented above for balance.

---

## Summary of items flagged for correction/further verification before final notebook use

1. **Lancet Regional Health – Europe (2024) WHO-Europe follow-up study** — cited in the prior summary but NOT independently re-verified this pass. Pull the real DOI/authors/numbers before citing.
2. **Lancet correction notice** for Watson et al. 2022 (DOI PIIS1473-3099(23)00566-2) — exists, was not read this pass; check before quoting exact headline figures.
3. **Oster et al. JAMA myocarditis paper** — exact DOI and full CIs not independently pulled this pass (PubMed returned a cookie-consent stub); numbers carried via secondary-source aggregation, consistent with but not directly re-verified against the prior summary.
4. **UK OpenSAFELY study's peer-reviewed journal version** — exact journal DOI not confirmed (ScienceDirect 403'd); only the medRxiv preprint DOI is confirmed directly.
5. **GVDN (Faksova et al. 2024) exact per-million/observed-vs-expected ratios** — qualitative signal-confirmation finding is verified; the underlying numeric tables were not accessible this pass (403 on ScienceDirect).
6. **The prior summary's "28-million-adult... per Gavi/vaccines work summary" citation** — very likely resolved by the French JAMA Network Open study (Semenzato et al. 2025, ~28.7M total) found this pass; recommend replacing the vague citation with this specific one, but note the population/geography (France, ages 18–59) should be stated explicitly rather than left generic.
