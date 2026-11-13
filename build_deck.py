"""Build the short Dutch COVID resilience deck (7 slides) as HTML and render it to PDF with headless Chrome.

Usage:  python build_deck.py ["COVID Resilience (NL, kort).pdf"]

Every number on the slides is computed here from the same code the app uses (resilience.py) plus
covid-resilience.db (built by build_resilience_db.py), so the deck can be rebuilt after the data
changes. Requires: pandas, pyarrow, covid-resilience.db and google-chrome on the PATH.
"""
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from resilience import (
    UN_MEMBER_ISO,
    country_metrics,
    load_daily,
    load_gdp_loss,
    load_health_capacity,
    load_society,
    rank_stability,
    score_countries,
)

HERE = Path(__file__).parent
DB = HERE / "covid-resilience.db"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "COVID Resilience (NL, kort).pdf"

CUTOFF = "2023-12-31"
WEIGHTS = {"health": 2, "economy": 1, "education": 1}
GITHUB = "https://github.com/filipvercauteren/covid/blob"
BRANCH = f"{GITHUB}/feature/COVID-2-covid-resilience"
PINNED = f"{GITHUB}/e990b9d89f50bff7b12196748c609c2f2f41c8fe"  # commit the line-number links point at
GH_URL = "https://github.com/filipvercauteren/covid"
APP_URL = "https://covid-resilience.streamlit.app/"
# Reported-deaths control (slide 7): leave out countries whose excess deaths exceed this multiple of reported deaths
CONTROL_RATIO = 3
TREND_START, TREND_END = 2015, 2019
LOSS_YEARS = (2020, 2021, 2022, 2023)

NL = {
    "Egypt": "Egypte", "Uzbekistan": "Oezbekistan", "Norway": "Noorwegen", "Albania": "Albanië",
    "Australia": "Australië", "Switzerland": "Zwitserland", "Israel": "Israël", "Luxembourg": "Luxemburg",
    "Belgium": "België", "Netherlands": "Nederland", "France": "Frankrijk", "Germany": "Duitsland",
    "Georgia": "Georgië", "Czechia": "Tsjechië", "Romania": "Roemenië", "Hungary": "Hongarije",
    "Denmark": "Denemarken", "New Zealand": "Nieuw-Zeeland", "Sweden": "Zweden", "Ireland": "Ierland",
}
MONTHS = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]


def nl(country):
    return NL.get(country, country)


def fmt(x, decimals=0):
    """Dutch number format: 1.234,5 with a real minus sign."""
    return f"{x:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def enumerate_nl(names):
    return ", ".join(names[:-1]) + " en " + names[-1]


def link(label, path, line=None):
    return f'<a href="{PINNED}/{path}#L{line}">{label}</a>' if line else f'<a href="{BRANCH}/{path}">{label}</a>'


# ---------------------------------------------------------------- data

def load_results():
    daily = load_daily()
    metrics = country_metrics(daily, load_gdp_loss(), load_society(), load_health_capacity(), CUTOFF)
    un = metrics[metrics["iso_code"].isin(UN_MEMBER_ISO)]
    scored, _ = score_countries(un, "excess_pm", WEIGHTS)

    controlled = un[~(un["excess_vs_reported"] > CONTROL_RATIO)]
    scored_control, _ = score_countries(controlled, "excess_pm", WEIGHTS)
    control_overlap = len(set(scored.head(10)["location"]) & set(scored_control.head(10)["location"]))

    stability, _ = rank_stability(un, "excess_pm", list(WEIGHTS), step=0.1, top_n=10)
    return {
        "un": un, "scored": scored, "stability": stability,
        "n_un": len(un), "n_excess": int(un["excess_pm"].notna().sum()), "n_rank": len(scored),
        "control_n": len(scored_control), "control_overlap": control_overlap,
    }


def load_db_facts():
    """Raw-table facts (row counts, Belgium's raw series) that are not in the exported parquet files."""
    con = sqlite3.connect(DB)

    def query(sql, *params):
        return pd.read_sql(sql, con, params=params)

    belgium = query(
        "select date, excess_mortality_cumulative_per_million as e from covid_data "
        "where location = 'Belgium' and date(date) <= ? order by date", CUTOFF,
    )
    belgium["date"] = pd.to_datetime(belgium["date"])
    excess = belgium.dropna()
    school = query(
        "select c1m_school_closing as c from oxcgrt_daily where iso_code = 'BEL' "
        "and date(date) between '2020-01-01' and '2022-12-31'"
    )
    return {
        "daily_rows": int(query("select count(*) as n from covid_data").n[0]),
        "countries": int(query("select count(distinct location) as n from covid_data where continent is not null").n[0]),
        "vaccine_countries": int(query("select count(distinct location) as n from vaccinations_by_manufacturer").n[0]),
        "bel_rows": len(belgium), "bel_excess": excess,
        "school_days": len(school), "school_full_days": int((school["c"] == 3).sum()),
        "gdp": query("select year, gdp_constant_2015_usd as g from gdp_annual where iso_code = 'BEL'").set_index("year").g,
    }


def gdp_series(gdp):
    """Actual vs trend GDP (2019 = 100), same formula as gdp_loss_for_country() in build_resilience_db.py."""
    growth = (gdp[TREND_END] / gdp[TREND_START]) ** (1 / (TREND_END - TREND_START)) - 1
    years = [TREND_END, *LOSS_YEARS]
    actual = {y: 100 * gdp[y] / gdp[TREND_END] for y in years}
    trend = {y: 100 * (1 + growth) ** (y - TREND_END) for y in years}
    expected, real = (sum(s[y] for y in LOSS_YEARS) for s in (trend, actual))
    return actual, trend, growth, 100 * (expected - real) / expected


# ---------------------------------------------------------------- css

CSS = """
@page{size:720pt 404.88pt;margin:0}
*{box-sizing:border-box}
html{zoom:.75}
body{margin:0;background:#f6f4ef;font-family:"IBM Plex Sans","Liberation Sans",Arial,sans-serif;color:#14213d}
.slide{position:relative;width:1280px;height:720px;overflow:hidden;page-break-after:always;padding:60px 76px 0}
.slide:last-child{page-break-after:auto}
.k{color:#c4501b;font-weight:700;font-size:15px;letter-spacing:.12em;text-transform:uppercase}
h1{font-size:40px;margin:10px 0 22px;line-height:1.12;font-weight:700;letter-spacing:-.01em}
.card{background:#fff;border:1px solid #e3dfd6;border-radius:8px;padding:18px 22px}
.card h3{margin:0 0 4px;font-size:14px;letter-spacing:.06em;text-transform:uppercase;color:#c4501b}
.card h2{margin:0 0 8px;font-size:21px}
.card p{font-size:16.5px;line-height:1.45;color:#2b3550;margin:0 0 6px}
.dark{background:#14213d;border-color:#14213d}.dark h2,.dark p{color:#fff}.dark h3{color:#f0a37a}
.dark a{color:#f0a37a}
.row{display:flex;gap:18px;align-items:stretch}
.arrow{align-self:center;font-size:28px;color:#8a90a3}
.foot{position:absolute;left:76px;bottom:30px;font-size:14px;color:#6b7185}
.note{font-size:17px;line-height:1.5;color:#2b3550}
a{color:#2f6f9f;font-weight:700}
a::after{content:" ↗";font-weight:400}
code{font-family:"DejaVu Sans Mono",monospace;font-size:14px;background:#f1eee7;padding:1px 5px;border-radius:3px}
.mono{font-family:"DejaVu Sans Mono",monospace;color:#4a5270;font-size:13.5px;line-height:1.35;display:block}
.ai{position:absolute;left:76px;bottom:30px;font-size:13px;color:#6b7185;letter-spacing:.08em}
.ai b{color:#c4501b}
.sm{display:inline-flex;flex-direction:column;align-items:center;vertical-align:middle;line-height:1;margin:0 2px}
.sm small{font-size:11px;line-height:1.15}.sm b{font-size:26px;font-weight:400}
.fr{display:inline-flex;flex-direction:column;align-items:center;vertical-align:middle;margin:0 4px}
.fr>span:first-child{border-bottom:1.5px solid #14213d;padding:0 6px 3px}.fr>span:last-child{padding-top:3px}
.f{font-family:"DejaVu Serif","Times New Roman",serif;font-size:20px;line-height:1.7;white-space:nowrap}
.dropped{border:2px dashed #b9b6ad;border-radius:8px;padding:12px 20px;margin-top:28px}
.dropped .t{font-size:14px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#6b7185}
.chip{flex:1;background:#eae7df;border-radius:6px;padding:8px 12px;font-size:15px;color:#2b3550}
.chip s{font-weight:700}
.col{flex:1}.col .k{font-size:13px;margin-bottom:6px}
.col .card{height:160px;padding:14px 18px}.col .card p{font-size:15px}
.col>p{font-size:15px;margin:10px 0 0;color:#2b3550}
.stat{font-size:34px;font-weight:700;line-height:1.1;color:#fff}
"""


def slide(inner):
    return f'<div class="slide">{inner}</div>'


# ---------------------------------------------------------------- slides

def slide_title():
    return slide(f"""
<div class="k" style="margin-top:130px">COVID-veerkracht</div>
<h1 style="font-size:64px;max-width:900px;margin-top:20px">Welke landen kwamen<br>het best door COVID-19?</h1>
<p class="note" style="font-size:22px;margin:10px 0 0;white-space:nowrap">3 criteria, 3 datasets van Our World in Data, Oxford en de Wereldbank, en 1 transparante gewogen score.</p>
<p class="note" style="font-size:17px;margin:22px 0 0">Live: <a href="{APP_URL}">{APP_URL}</a> &nbsp;·&nbsp; Code: {link(GH_URL, "README.md")}</p>
<div class="ai"><b>AI-GEGENEREERD</b> &nbsp; Analyse, code en slides gegenereerd door Claude (Anthropic AI)</div>""")


def slide_question(db):
    return slide(f"""
<div class="k">De onderzoeksvraag</div>
<h1>Veerkracht is niet in 1 getal te vatten</h1>
<p class="note" style="max-width:1020px">Het project begon als zoektocht naar het beste vaccin, maar vaccinmerk-data bestaat voor slechts
{db["vaccine_countries"]} landen (tegenover {db["countries"]} landen en gebieden in de hoofddataset). Dus werd de vraag breder:</p>
<p style="font-size:34px;font-weight:700;margin:14px 0 26px">Welke landen kwamen het best door COVID-19?</p>
<div class="row">
 <div class="card" style="flex:1"><h3>Gezondheid · weegt {WEIGHTS["health"]}</h3><h2>Oversterfte</h2>
  <p>Extra sterfgevallen per miljoen inwoners ten opzichte van normaal, tot eind 2023</p></div>
 <div class="card" style="flex:1"><h3>Economie · weegt {WEIGHTS["economy"]}</h3><h2>BBP-verlies</h2>
  <p>2020–23 ten opzichte van de groeitrend van 2015–19</p></div>
 <div class="card" style="flex:1"><h3>Onderwijs · weegt {WEIGHTS["education"]}</h3><h2>Schoolsluitingen</h2>
  <p>Weken dat scholen volledig gesloten waren, 2020–22</p></div>
</div>
<p class="note" style="margin-top:20px;font-size:16px;color:#4a5270">Drie criteria, lager is overal beter. Einddatum en gewichten zijn aanpasbaar in de app.</p>
<p class="note" style="margin-top:-6px;font-size:13.5px;color:#6b7185"><b>Waarom de einddatum aanpassen?</b> De COVID-periode loopt van 11/03/2020 tot 05/05/2023. Landen die het virus vroeg buiten hielden (Nieuw-Zeeland, Australië) scoren veel beter bij einde 2021 dan bij einde 2023. Einde 2023 is de eerlijkste standaard.</p>
<div class="dropped"><div class="t">Van 6 naar 3 criteria</div>
 <p class="note" style="font-size:16px;margin:4px 0 10px">We startten met zes criteria en lieten er drie vallen om de complexiteit te beperken. Ze blijven wel als context zichtbaar in de app, maar tellen niet mee in de score.</p>
 <div class="row" style="gap:14px">
  <div class="chip"><s>Banen</s> · stijging van de werkloosheid</div>
  <div class="chip"><s>Vrijheid</s> · stringency-index</div>
  <div class="chip"><s>Herstel</s> · jaren met BBP onder 2019-niveau</div></div></div>""")


def bar(rank, name, score, highlight=False):
    colour = "#c4501b" if highlight else "#14213d"
    weight = "font-weight:700;" if highlight else ""
    return (f'<div style="display:flex;align-items:center;height:29px"><div style="width:34px;text-align:right;'
            f'color:#6b7185;font-size:15px">{rank}</div><div style="width:150px;padding-left:12px;font-size:16px;{weight}">{name}</div>'
            f'<div style="width:400px;background:#e9e5db;height:15px;border-radius:3px">'
            f'<div style="width:{score:.0f}%;background:{colour};height:15px;border-radius:3px"></div></div>'
            f'<div style="width:46px;text-align:right;font-size:15px;font-weight:700">{score:.0f}</div></div>')


def slide_answer(r):
    scored = r["scored"]

    def row(country):
        return scored[scored["location"] == country].iloc[0]

    dots = '<div style="height:20px;color:#8a90a3;padding-left:46px">· · ·</div>'
    top, bottom = scored[scored["rank"] <= 10], scored.tail(3)
    belgium = row("Belgium")
    bars = [bar(int(x["rank"]), nl(x["location"]), x["score"]) for _, x in top.iterrows()]
    bars += [dots, bar(int(belgium["rank"]), "België", belgium["score"], True), dots]
    bars += [bar(int(x["rank"]), nl(x["location"]), x["score"]) for _, x in bottom.iterrows()]
    ranks = {c: int(row(c)["rank"]) for c in ("Belgium", "Netherlands", "France", "Germany")}
    best = enumerate_nl([nl(c) for c in scored.head(3)["location"]])
    worst = enumerate_nl([nl(c) for c in bottom["location"]])
    return slide(f"""
<div class="k">Het antwoord</div>
<h1 style="font-size:36px">{best} komen het best uit de bus</h1>
<div class="note" style="font-size:14.5px;color:#6b7185;margin:-8px 0 12px">Score 0–100 (100 = best op elk criterium) · {r["n_rank"]} landen met alle drie de criteria · einde 2023 · trendbasislijn · gewichten {"-".join(str(w) for w in WEIGHTS.values())}</div>
<div style="display:flex;gap:30px">
 <div style="width:660px">{"".join(bars)}</div>
 <div class="card" style="flex:1;align-self:flex-start;margin-top:6px"><h2 style="font-size:20px">Wat valt op</h2>
  <p>De top 10 combineert een oversterfte van <b>{fmt(top["excess_pm"].min())} tot {fmt(top["excess_pm"].max())}</b> per miljoen met een BBP-verlies van hoogstens {fmt(top["gdp_loss_pct"].max(), 1)}%. {nl(scored.iloc[0]["location"])} heeft zelfs minder sterfgevallen dan verwacht.</p>
  <p>Onderaan: <b>{worst}</b>, met {fmt(bottom["excess_pm"].min())}–{fmt(bottom["excess_pm"].max())} oversterfte per miljoen. Mexico sloot scholen bovendien {fmt(row("Mexico")["school_weeks_full"])} weken volledig.</p>
  <p><b>België en zijn buren:</b> België {ranks["Belgium"]}e, Nederland {ranks["Netherlands"]}e, Frankrijk {ranks["France"]}e, Duitsland {ranks["Germany"]}e.</p>
  <p style="color:#4a5270">De volgorde hangt af van de gewichten; de groep aan kop blijft stabiel (zie app, tabblad Weight sensitivity).</p></div>
</div>
<div class="foot">{link("score_countries()", "resilience.py", 238)} in resilience.py · standaardinstellingen van de app · Streamlit-tabblad Ranking</div>""")


def slide_path(r, db):
    parquet_mb = sum(p.stat().st_size for p in (HERE / "app-data").glob("*.parquet")) / 1e6
    worldbank = "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.KD?format=json&amp;per_page=20000&amp;date=2010:2025"
    return slide(f"""
<div class="k">Het pad · van ruwe data tot score</div>
<h1>Drie open bronnen, vier stappen, één rij per land</h1>
<div class="row">
 <div class="card" style="flex:1.15"><h3>1 · Ruwe bronnen</h3>
  <p><a href="https://github.com/owid/covid-19-data">OWID</a> (dagelijks): oversterfte</p>
  <p><a href="https://github.com/OxCGRT/covid-policy-dataset">Oxford OxCGRT</a> (dagelijks): schoolsluitingen</p>
  <p><a href="{worldbank}">Wereldbank</a> (jaarlijks): BBP</p>
  <p style="font-size:13.5px;color:#6b7185">Klik op een bron om de dataset te openen</p></div>
 <div class="arrow">→</div>
 <div class="card" style="flex:1"><h3>2 · SQLite, {DB.stat().st_size // 1_000_000} MB</h3><p><b>covid-resilience.db</b>: ruwe tabellen plus afgeleide tabellen (BBP-verlies, schoolweken…), eenmalig berekend in <code>build_resilience_db.py</code></p></div>
 <div class="arrow">→</div>
 <div class="card" style="flex:.9"><h3>3 · Parquet</h3><p>{fmt(parquet_mb, 1)} MB in git (de database is te groot voor GitHub)</p></div>
 <div class="arrow">→</div>
 <div class="card dark" style="flex:1.1"><h3>4 · Live in de app</h3><p>{link("resilience.py", "resilience.py")}:<br>één rij per land →<br>rangen → gewogen score</p></div>
</div>
<div class="row" style="margin-top:22px">
 <div class="card" style="flex:1;text-align:center"><div style="font-size:46px;font-weight:700;color:#c4501b">{fmt(db["daily_rows"])}</div><p>dagrijen uit OWID<br>({db["countries"]} landen en gebieden)</p></div>
 <div class="card" style="flex:1;text-align:center"><div style="font-size:46px;font-weight:700;color:#2f6f9f">{r["n_un"]}</div><p>VN-lidstaten<br>({r["n_excess"]} met oversterfte-data)</p></div>
 <div class="card" style="flex:1;text-align:center"><div style="font-size:46px;font-weight:700">{r["n_rank"]}</div><p>landen met alle drie de criteria<br>= de ranking</p></div>
</div>
<p class="note" style="margin-top:20px"><b>Niet-triviaal:</b> het samenbrengen van dag- en jaardata (volgende slide) en het BBP-verlies tegenover een wereld zonder COVID (daarna). De rest is bronnen ophalen en filteren.</p>""")


def slide_join(r, db):
    excess = db["bel_excess"]
    first, last = excess.iloc[0], excess.iloc[-1]
    december = excess[excess["date"] <= "2023-12-10"].iloc[-1]

    def line(point):
        d = point["date"]
        return f'<span class="mono">{d.day} {MONTHS[d.month - 1]} {d.year} … {fmt(point["e"])}</span>'

    belgium = r["un"][r["un"]["location"] == "Belgium"].iloc[0]
    return slide(f"""
<div class="k">Het pad · niet-triviaal 1</div>
<h1>Van verschillende datasets naar 1 rij per land</h1>
<p class="note" style="margin:-8px 0 12px">De ruwe data heeft per land honderden tot duizenden rijen, en elke bron heeft een ander ritme. Per maatstaf vatten we ze samen tot één getal; hoe, hangt af van wat de reeks betekent. Voorbeeld: <b>België</b>, einddatum 31 december 2023.</p>
<div class="row" style="gap:28px">
 <div class="col"><div class="k">Oversterfte · OWID, dagelijks</div>
  <div class="card"><p><b>{fmt(db["bel_rows"])} dagrijen</b> (2020 → 2023), maar slechts {fmt(len(excess))} met een oversterftewaarde. Die waarde is <b>cumulatief</b>:</p>
   {line(first)}{line(december)}{line(last)}</div>
  <p>↓ <b>Laatste waarde</b> tot de einddatum. Cumulatief, dus het eindniveau telt, niet de som.</p></div>
 <div class="col"><div class="k">Schoolsluitingen · Oxford, dagelijks</div>
  <div class="card"><p><b>{fmt(db["school_days"])} dagrijen</b> (2020–22), met per dag een score voor schoolsluiting (0–3):</p>
   <span class="mono">C1M = 3: scholen op alle</span><span class="mono">niveaus verplicht dicht</span><span class="mono">→ {db["school_full_days"]} van de {fmt(db["school_days"])} dagen</span></div>
  <p>↓ <b>Dagen tellen ÷ 7</b>: {db["school_full_days"]} dagen = {fmt(db["school_full_days"] / 7, 1)} weken volledig gesloten.</p></div>
 <div class="col"><div class="k">BBP-verlies · Wereldbank, jaarlijks</div>
  <div class="card"><p><b>Jaarcijfers</b> 2015–2023, dus geen dagen. De trend uit 2015–19 loopt door als verwachte groei zonder COVID:</p>
   <span class="mono">werkelijk 2020–23 vs. trend</span><span class="mono">over 4 jaar opgeteld</span></div>
  <p>↓ <b>Vast venster 2020–23</b>: niets omgerekend naar dagen.</p></div>
</div>
<div class="card dark" style="margin-top:22px;padding:12px 22px"><h3 style="margin:0 0 6px">Één rij · België · een left join op de ISO-code (BEL)</h3>
 <div style="display:flex">
  <div style="flex:1"><div class="stat">{fmt(belgium["excess_pm"])}</div><p style="margin:0">oversterfte per miljoen</p></div>
  <div style="flex:1"><div class="stat">{fmt(belgium["school_weeks_full"], 1)}</div><p style="margin:0">schoolweken volledig gesloten</p></div>
  <div style="flex:1"><div class="stat">{fmt(belgium["gdp_loss_pct"], 1)}%</div><p style="margin:0">BBP-verlies t.o.v. trend</p></div></div></div>
<p class="note" style="margin-top:20px;font-size:16px"><b>Koppeling:</b> alle datasets dragen voor de {r["n_un"]} VN-lidstaten dezelfde ISO-3-code, dus er is geen mapping nodig en er wordt niets geïnterpoleerd. <b>Let op:</b> oversterfte volgt de einddatum, BBP-verlies beslaat altijd 2020–23. Gemelde sterfte (alleen ter controle) is ook cumulatief: het maximum is het eindtotaal, de som zou dubbel tellen.</p>
<div class="foot">{link("country_metrics(cutoff)", "resilience.py", 146)} · groupby("location") · left join op ISO-code (pandas merge) in resilience.py</div>""")


def slide_gdp(r, db):
    actual, trend, growth, loss = gdp_series(db["gdp"])
    years = [TREND_END, *LOSS_YEARS]
    x0, x1, y0, y1, lo, hi = 70, 560, 40, 300, 94, 109
    px = lambda i: x0 + i * (x1 - x0) / 4
    py = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    pts = lambda series: " ".join(f"{px(i)},{py(series[y])}" for i, y in enumerate(years))
    svg = ['<svg width="660" height="360" viewBox="0 0 660 360" font-family="Liberation Sans,Arial">']
    for v in (95, 100, 105):
        svg.append(f'<line x1="{x0}" y1="{py(v)}" x2="{x1}" y2="{py(v)}" stroke="#d9d4c8"/>'
                   f'<text x="{x0 - 10}" y="{py(v) + 5}" text-anchor="end" font-size="13" fill="#6b7185">{v}</text>')
    svg += [f'<text x="{px(i)}" y="{y1 + 26}" text-anchor="middle" font-size="14" fill="#6b7185">{y}</text>' for i, y in enumerate(years)]
    svg.append(f'<polyline points="{pts(trend)}" fill="none" stroke="#c4501b" stroke-width="3" stroke-dasharray="8 6"/>')
    svg.append(f'<polyline points="{pts(actual)}" fill="none" stroke="#14213d" stroke-width="3.5"/>')
    svg += [f'<circle cx="{px(i)}" cy="{py(actual[y])}" r="5" fill="#14213d"/>' for i, y in enumerate(years)]
    svg.append(f'<text x="{px(1) + 10}" y="{py(actual[2020]) + 24}" font-size="14" fill="#14213d">2020: {fmt(actual[2020] - 100, 1)}% i.p.v. +{fmt(100 * growth, 1)}% verwacht</text>')
    svg.append(f'<text x="{px(3)}" y="{py(trend[2022]) - 26}" font-size="14" fill="#c4501b" text-anchor="middle">trend 2015–19</text>')
    svg.append(f'<text x="{px(3)}" y="{py(actual[2022]) + 30}" font-size="14" fill="#14213d" text-anchor="middle">werkelijk</text>')
    svg.append(f'<text x="{(x0 + x1) / 2}" y="345" text-anchor="middle" font-size="13" fill="#6b7185">België, reëel BBP (2019 = 100)</text></svg>')
    sigma = '<span class="sm"><small>2023</small><b>Σ</b><small>y=2020</small></span>'
    ranked = r["un"].dropna(subset=["gdp_loss_pct"])
    ireland = ranked[ranked["location"] == "Ireland"].iloc[0]  # example: multinational-driven GDP boom
    return slide(f"""
<div class="k">Het pad · niet-triviaal 2</div>
<h1>BBP-verlies: afgemeten aan een wereld zonder COVID</h1>
<div style="display:flex;gap:30px">
 <div style="width:660px">{"".join(svg)}</div>
 <div style="flex:1"><div class="card"><p>De vraag is niet “is het BBP gekrompen?” maar <b>“hoeveel lager ligt het dan zonder COVID?”</b> Daarvoor hebben we een basislijn nodig: de gemiddelde groei van 2015–19, doorgetrokken.</p>
  <p>België 2020–23: <b>{fmt(loss, 1)}% verlies</b>. Negatief = beter dan verwacht (Ierland: {fmt(ireland["gdp_loss_pct"], 1)}%).</p>
  <p style="color:#4a5270">Nadeel: de trend overschat het verlies voor landen die voor COVID snel groeiden.</p></div></div>
</div>
<div class="card" style="margin-top:6px;padding:10px 22px"><div class="f"><i>g</i> = (BBP<sub>2019</sub> / BBP<sub>2015</sub>)<sup>1/4</sup> − 1 &nbsp;&nbsp; <i>V</i>(<i>y</i>) = BBP<sub>2019</sub> × (1 + <i>g</i>)<sup><i>y</i>−2019</sup>
&nbsp;&nbsp; Verlies % = <span class="fr"><span>{sigma} <i>V</i>(<i>y</i>) − {sigma} <i>W</i>(<i>y</i>)</span><span>{sigma} <i>V</i>(<i>y</i>)</span></span> × 100</div>
<div style="font-size:13.5px;color:#6b7185">g = gemiddelde jaarlijkse BBP-groei 2015 tot 2019 (4 jaar, dus exponent 1/4) · V = verwacht, W = werkelijk BBP (constante 2015 US$), gesommeerd over 2020 tot 2023</div></div>
<div class="foot">Tabel {link("gdp_covid_loss", "build_resilience_db.py", 165)} · gdp_loss_for_country() in build_resilience_db.py · Wereldbank</div>""")


def slide_conclusion(r):
    scored, stability = r["scored"], r["stability"]
    ratio = r["un"].set_index("location")["excess_vs_reported"]
    stable = enumerate_nl([nl(c) for c in stability[stability["pct_in_top"] >= 50]["location"].head(5)])
    return slide(f"""
<div class="k">Beperkingen en conclusie</div>
<h1>Wat je moet onthouden</h1>
<div class="row" style="flex-wrap:wrap">
 <div class="card" style="flex:1 1 46%"><h2 style="font-size:19px">Slechts {r["n_rank"]} van {r["n_un"]} VN-lidstaten</h2><p>Oversterfte bestaat alleen waar sterfte goed wordt geregistreerd: vooral Europa, Noord-Amerika en delen van Azië. Afrika en een groot deel van Azië ontbreken.</p></div>
 <div class="card" style="flex:1 1 46%"><h2 style="font-size:19px">Controle met gemelde sterfte</h2><p><b>Het probleem met gemelde COVID-doden:</b> ze tellen alleen sterfgevallen die getest, vastgesteld en gemeld zijn. Landen met weinig testen of zwakke registratie lijken daardoor veel beter dan ze zijn (Egypte: {fmt(ratio["Egypt"])}×, Oezbekistan: {fmt(ratio["Uzbekistan"])}× minder dan de oversterfte). Oversterfte vergelijkt álle sterfgevallen met wat normaal is, ongeacht de oorzaak. Sluit je die landen uit ({r["control_n"]} blijven over), dan blijven {r["control_overlap"]} van de 10 in de top 10.</p></div>
</div>
<div class="card dark" style="margin-top:18px"><p><b>Conclusie:</b> tot eind 2023 komen {enumerate_nl([nl(c) for c in scored.head(3)["location"]])} het best uit de bus volgens drie expliciete criteria. {stable} blijven in de meeste gewichtscombinaties in de top 10.</p></div>
<div class="ai"><b>AI-GEGENEREERD</b> &nbsp; Analyse, code en slides gegenereerd door Claude (Anthropic AI)</div>""")


# ---------------------------------------------------------------- build

def main():
    results, db = load_results(), load_db_facts()
    slides = [slide_title(), slide_question(db), slide_answer(results), slide_path(results, db),
              slide_join(results, db), slide_gdp(results, db), slide_conclusion(results)]
    html = (f'<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>COVID Resilience</title>'
            f"<style>{CSS}</style></head><body>{''.join(slides)}</body></html>")
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome is None:
        sys.exit("google-chrome or chromium is required to render the PDF")
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "deck.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={OUT.resolve()}", page.as_uri()], check=True, capture_output=True)
    print("written", OUT)


if __name__ == "__main__":
    main()
