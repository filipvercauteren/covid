"""Which countries coped best with COVID-19? - Streamlit app.

Run with:  streamlit run resilience_app.py
Needs covid-combo.db (tables covid_data and gdp_covid_loss), see sources.md.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from resilience import (
    CAPACITY_COLUMNS,
    COLUMN_LABELS,
    COST_CRITERIA,
    CRITERIA_LABELS,
    CUTOFFS,
    DB_PATH,
    GDP_BASELINES,
    HEALTH_MEASURES,
    VAX_THRESHOLD,
    add_age_adjusted_excess,
    capacity_correlations,
    country_metrics,
    criterion_columns,
    excess_timeseries,
    load_daily,
    load_gdp_loss,
    load_health_capacity,
    load_society,
    rank_stability,
    score_countries,
    select_peers,
    vaccination_timeseries,
    with_gdp_baseline,
)

DEFAULT_HIGHLIGHT = ("Belgium",)
DEFAULT_PEERS = ("Belgium", "Netherlands", "Germany", "France", "Denmark", "Sweden", "Norway",
                 "United Kingdom", "Austria", "Switzerland", "Italy", "Spain")
DEFAULT_TIMELINE = ("New Zealand", "Australia", "Japan", "Belgium", "Sweden", "Denmark")
DEFAULT_WEIGHTS = {"health": 5, "economy": 2, "jobs": 1, "education": 1, "freedom": 1, "recovery": 1}


# ---------------------------------------------------------------- data (cached)

@st.cache_data(show_spinner="Loading covid-combo.db…")
def cached_daily() -> pd.DataFrame:
    return load_daily(DB_PATH)


@st.cache_data(show_spinner=False)
def cached_metrics(cutoff: str) -> pd.DataFrame:
    return country_metrics(
        cached_daily(), load_gdp_loss(DB_PATH), load_society(DB_PATH), load_health_capacity(DB_PATH), cutoff
    )


@st.cache_data(show_spinner=False)
def peer_table(
    cutoff: str,
    gdp_baseline: str,
    min_population: int,
    continents: tuple[str, ...],
    countries: tuple[str, ...],
) -> tuple[pd.DataFrame, float, float]:
    """Metrics for the peer group. The age fit uses every country above the
    population threshold (more stable than fitting on a small peer group)."""
    metrics = with_gdp_baseline(select_peers(cached_metrics(cutoff), min_population), gdp_baseline)
    adjusted, slope, corr = add_age_adjusted_excess(metrics)
    return select_peers(adjusted, 0, continents, countries), slope, corr


def label(column: str) -> str:
    return COLUMN_LABELS.get(column, column)


# ---------------------------------------------------------------- page setup

st.set_page_config(
    page_title="Who coped best with COVID-19?",
    page_icon=":material/public:",
    layout="wide",
)

if not Path(DB_PATH).exists():
    st.error(f"`{DB_PATH}` not found. Build it first (see `sources.md`), then reload.")
    st.stop()

"# Who coped best with COVID-19?"
st.caption(
    "\"Coped best\" isn't a single number: choose what counts, and the ranking follows. "
    "Lower is better on every criterion. Data: OWID, OxCGRT, World Bank — see `sources.md`."
)

all_metrics = cached_metrics(CUTOFFS[-1])
all_countries = sorted(all_metrics["location"])
all_continents = sorted(all_metrics["continent"].dropna().unique())

with st.sidebar:
    st.markdown("### Settings")

    cutoff = st.select_slider(
        "Deaths measured up to",
        options=CUTOFFS,
        value=CUTOFFS[-1],
        format_func=lambda d: d[:4] + " (end)",
        help="Pitfall 1: countries that kept the virus out early (NZ, Australia) look much "
        "better at end-2021 than at end-2023. End 2023 is the fairest default.",
    )
    health_column = st.radio(
        "Health measure",
        list(HEALTH_MEASURES),
        format_func=HEALTH_MEASURES.get,
        help="Excess mortality counts all extra deaths and isn't fooled by poor testing. "
        "Reported COVID deaths depend on testing and definitions.",
    )
    gdp_baseline = st.radio(
        "GDP baseline (what GDP would have been without COVID)",
        list(GDP_BASELINES),
        format_func=lambda key: GDP_BASELINES[key][1],
        help="IMF forecast: what the IMF expected in October 2019, before COVID was known — the "
        "standard method. Trend: 2015–2019 growth continued, which overstates the loss for countries "
        "that were growing fast before COVID (e.g. Spain, Poland, Ireland). Compare both to see "
        "whether a country's position depends on the method.",
    )

    peer_mode = st.segmented_control(
        "Compare with",
        ["All countries", "Continents", "Custom group"],
        default="All countries",
        required=True,
        help="Pitfall 2: compare like with like.",
    )
    peer_continents: tuple[str, ...] = ()
    peer_countries: tuple[str, ...] = ()
    if peer_mode == "Continents":
        peer_continents = tuple(st.multiselect("Continents", all_continents, default=["Europe"]))
    elif peer_mode == "Custom group":
        peer_countries = tuple(st.multiselect(
            "Countries", all_countries, default=[c for c in DEFAULT_PEERS if c in all_countries]
        ))

    min_population = st.number_input(
        "Minimum population", min_value=0, value=1_000_000, step=500_000,
        help="Very small countries make the per-million figures noisy.",
    )
    highlight = st.multiselect(
        "Highlight countries", all_countries,
        default=[c for c in DEFAULT_HIGHLIGHT if c in all_countries],
    )

peers, age_slope, age_corr = peer_table(
    cutoff, gdp_baseline, int(min_population), peer_continents, peer_countries
)
baseline_label = GDP_BASELINES[gdp_baseline][1]

if peers.empty:
    st.warning("No countries match these settings.")
    st.stop()

tabs = st.tabs([
    ":material/checklist: Criteria",
    ":material/scatter_plot: Deaths vs. cost",
    ":material/leaderboard: Ranking",
    ":material/balance: Weight sensitivity",
    ":material/timeline: End date matters",
    ":material/vaccines: Vaccination speed",
    ":material/local_hospital: Healthcare capacity",
    ":material/fact_check: Data quality",
])

# ---------------------------------------------------------------- 1. criteria

with tabs[0]:
    st.markdown(
        """
| Group | Criterion | Used here | Source column |
|---|---|---|---|
| **Health** | Excess deaths per million | ✅ main measure | `excess_mortality_cumulative_per_million` |
| | Age-adjusted excess deaths | ⚠️ rough linear correction on % aged 65+ | `aged_65_older` |
| | Reported COVID deaths | ✅ for comparison only | `total_deaths_per_million` |
| | Life-expectancy drop 2019 → worst of 2020–22 | ✅ alternative health measure | `society_covid` (World Bank) |
| | Hospital overload | ⚠️ shown, not scored — ICU data for ~40 countries | `icu_patients_per_million` |
| | Years of life lost | ❌ not available | — |
| **Economy** | GDP loss 2020–23 vs. a no-COVID baseline: IMF forecast of Oct 2019 (default) or 2015–19 trend | ✅ "economy" criterion | `gdp_covid_loss` (World Bank + IMF) |
| | Unemployment rise 2019 → worst of 2020–22 | ✅ "jobs" criterion | `society_covid` (World Bank / ILO) |
| | Government debt, support costs | ❌ debt data for only ~30 of these countries | — |
| **Society** | Weeks schools fully closed 2020–22 | ✅ "education" criterion | `society_covid` (OxCGRT C1M = 3) |
| | Restrictions (stringency) | ✅ "freedom" criterion | `stringency_index` (OxCGRT) |
| | Mobility (actual behaviour) | ❌ Google data missing for ~10% of these countries | — |
| | Learning loss, mental health | ❌ not available for all countries | — |
| **Resilience** | Years GDP below its 2019 level (2020–24) | ✅ "recovery" criterion | `gdp_covid_loss` (World Bank) |
| | Vaccination speed | ✅ shown, not scored | `people_fully_vaccinated_per_hundred` |
| | Healthcare capacity before COVID (spending, doctors, nurses, beds) | ✅ explanatory, not scored — see *Healthcare capacity* | `health_capacity` (World Bank) |
"""
    )
    st.markdown("##### Coverage in the current peer group")
    coverage = {
        "Countries": len(peers),
        "Excess mortality": peers["excess_pm"].notna().sum(),
        "GDP loss": peers["gdp_loss_pct"].notna().sum(),
        "Unemployment": peers["unemployment_rise_pp"].notna().sum(),
        "School closures": peers["school_weeks_full"].notna().sum(),
        "Stringency": peers["avg_stringency"].notna().sum(),
        "Life expectancy": peers["life_expectancy_drop_years"].notna().sum(),
        "GDP recovery": peers["gdp_years_below_2019"].notna().sum(),
        "ICU data": peers["peak_icu_pm"].notna().sum(),
    }
    for col, (name, count) in zip(st.columns(len(coverage)), coverage.items()):
        col.metric(name, int(count))

    with st.expander("Methodological pitfalls that change the ranking"):
        st.markdown(
            """
1. **The end date matters** — see *End date matters*. Use the sidebar slider.
2. **Compare like with like** — islands and young or wealthy countries have built-in advantages.
   Use *Compare with* to pick a peer group.
3. **Data quality** — countries with poor death registration are missing from excess mortality,
   or look better than reality. See *Data quality*.
4. **Weighting** — the weights largely decide the winner. See *Weight sensitivity*.
5. **The GDP baseline** — the loss is measured against what GDP *would* have been without COVID.
   The IMF's October 2019 forecast is the standard choice; extending the 2015–19 trend overstates
   the loss for fast-growing countries. A cautious IMF forecast flatters a country (Belgium is above
   the forecast from 2022). Switch *GDP baseline* in the sidebar to see if the ranking holds.

Also: GDP loss and unemployment include non-COVID shocks (energy crisis 2022, wars, oil booms);
stringency and school closures measure rules on paper, not how people behaved; the World Bank
unemployment figures are modelled ILO estimates.
"""
        )

# ---------------------------------------------------------------- 2. scatter

with tabs[1]:
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    cost_columns = list(COST_CRITERIA.values())
    x_column = c1.selectbox("Cost on the x axis", cost_columns, format_func=label)
    color_options = [c for c in cost_columns if c != x_column]
    color_column = c2.selectbox(
        "Dot colour", color_options, format_func=label,
        index=color_options.index("avg_stringency") if "avg_stringency" in color_options else 0,
    )
    max_gdp_loss = c3.slider(
        "Hide countries with |GDP loss| above (%)", 5, 50, 25,
        help="Very large values are mostly other shocks (oil booms, wars, tourism collapse).",
    )
    label_all = c4.toggle("Label all", value=len(peers) <= 30)

    plot = peers.dropna(subset=[health_column, x_column])
    plot = plot[plot["gdp_loss_pct"].abs().le(max_gdp_loss) | plot["gdp_loss_pct"].isna()]
    hidden = sorted(set(peers.dropna(subset=[health_column, x_column])["location"]) - set(plot["location"]))

    if plot.empty:
        st.info("No countries have both measures for these settings.")
    else:
        plot = plot.assign(text=[
            loc if (label_all or loc in highlight) else "" for loc in plot["location"]
        ])
        with_color = plot[plot[color_column].notna()]
        hover = {
            health_column: ":.0f", x_column: ":.1f", color_column: ":.1f",
            "pct_fully_vax": ":.0f", "population": ":,.0f", "text": False,
        }
        fig = px.scatter(
            with_color, x=x_column, y=health_column, color=color_column, size="population",
            size_max=45, text="text", hover_name="location", hover_data=hover,
            color_continuous_scale="Viridis_r", labels=COLUMN_LABELS,
        )
        without_color = plot[plot[color_column].isna()]
        if not without_color.empty:
            fig.add_trace(go.Scatter(
                x=without_color[x_column], y=without_color[health_column], mode="markers+text",
                text=without_color["text"], hovertext=without_color["location"],
                marker={"size": 10, "color": "rgba(0,0,0,0)", "line": {"color": "grey", "width": 1}},
                name=f"no {label(color_column).lower()}",
            ))
        highlighted = plot[plot["location"].isin(highlight)]
        if not highlighted.empty:
            fig.add_trace(go.Scatter(
                x=highlighted[x_column], y=highlighted[health_column], mode="markers",
                marker={"size": 22, "color": "rgba(0,0,0,0)", "line": {"color": "crimson", "width": 2}},
                hoverinfo="skip", name="highlighted",
            ))
        fig.update_traces(textposition="top center", textfont_size=10, selector={"mode": "markers+text"})
        fig.add_vline(x=plot[x_column].median(), line_dash="dash", line_color="grey")
        fig.add_hline(y=plot[health_column].median(), line_dash="dash", line_color="grey")
        fig.add_annotation(xref="paper", yref="paper", x=0.01, y=0.01, showarrow=False,
                           text="few deaths, low cost", font={"color": "green"})
        fig.add_annotation(xref="paper", yref="paper", x=0.99, y=0.99, showarrow=False,
                           text="many deaths, high cost", font={"color": "firebrick"})
        fig.update_layout(height=650, legend={"orientation": "h", "y": -0.12},
                          coloraxis_colorbar={"title": label(color_column)})
        st.plotly_chart(fig)

        st.caption(
            f"{len(plot)} countries. Dashed lines = medians. Bubble size = population. "
            f"Excess/reported deaths measured up to end {cutoff[:4]}; GDP loss always 2020–23, "
            f"vs. {baseline_label}; "
            "unemployment, school closures and stringency 2020–22."
            + (f" Hidden as GDP outliers: {', '.join(hidden)}." if hidden else "")
        )
        if health_column == "excess_age_adj_pm":
            st.caption(
                f"Age adjustment: {age_slope:+.0f} excess deaths/million per extra %-point aged 65+ "
                f"(correlation {age_corr:.2f} — a weak relationship, so treat the correction as rough)."
            )

# ---------------------------------------------------------------- 3. ranking

with tabs[2]:
    st.markdown(
        "Each criterion is turned into a rank within the peer group, then combined with your weights. "
        "**Score 100** = best on every weighted criterion, **0** = worst."
    )
    weights = {
        name: col.slider(CRITERIA_LABELS[name], 0, 10, default)
        for col, (name, default) in zip(st.columns(len(DEFAULT_WEIGHTS)), DEFAULT_WEIGHTS.items())
    }

    if sum(weights.values()) == 0:
        st.warning("Give at least one criterion a weight above 0.")
    else:
        total = sum(weights.values())
        st.caption(" · ".join(f"{CRITERIA_LABELS[k]} {100 * w / total:.0f}%" for k, w in weights.items()))
        scored, missing = score_countries(peers, health_column, weights)
        columns = criterion_columns(health_column)

        shown_columns = [*columns.values(), "pct_fully_vax", "peak_icu_pm"]
        table = scored[["rank", "location", "continent", "score", *shown_columns]]
        st.dataframe(
            table,
            hide_index=True,
            height=min(38 * (len(table) + 1), 700),
            column_config={
                "rank": st.column_config.NumberColumn("#", format="%d", width="small"),
                "location": "Country",
                "continent": "Continent",
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                **{
                    c: st.column_config.NumberColumn(label(c), format="%.0f" if c.endswith("_pm") else "%.1f")
                    for c in shown_columns
                },
            },
        )
        for country in highlight:
            row = scored[scored["location"] == country]
            if not row.empty:
                st.caption(f"**{country}**: rank {int(row['rank'].iloc[0])} of {len(scored)}.")
        if missing:
            with st.expander(f"{len(missing)} countries left out (missing a weighted criterion)"):
                st.write(", ".join(missing))

# ---------------------------------------------------------------- 4. weight sensitivity

with tabs[3]:
    st.markdown(
        "Pitfall 4: the weights can decide the winner. Here every combination of weights "
        "(steps of 10%, summing to 100%) is tried. Countries with a **narrow bar near the top** "
        "come out well whatever you value; long bars depend on the weights."
    )
    c1, c2 = st.columns([3, 1])
    sensitivity_criteria = c1.multiselect(
        "Criteria to vary", list(CRITERIA_LABELS), format_func=CRITERIA_LABELS.get,
        default=[name for name, w in weights.items() if w > 0] or list(CRITERIA_LABELS),
        help="Defaults to the criteria with a weight above 0 in the Ranking tab.",
    )
    top_n = c2.slider("Count as 'top' when ranked in the first", 3, 25, 10)

    stability, n_combos = (
        rank_stability(peers, health_column, sensitivity_criteria, step=0.1, top_n=top_n)
        if len(sensitivity_criteria) >= 2
        else (pd.DataFrame(), 0)
    )

    if len(sensitivity_criteria) < 2:
        st.info("Pick at least two criteria.")
    elif stability.empty:
        st.info("No countries have all selected criteria.")
    else:
        shown = stability.head(30).iloc[::-1]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=shown["location"], x=shown["worst_rank"] - shown["best_rank"] + 0.6,
            base=shown["best_rank"] - 0.3, orientation="h", name="best → worst rank",
            marker_color="lightsteelblue",
            customdata=shown[["best_rank", "worst_rank"]].to_numpy(),
            hovertemplate="%{y}: rank %{customdata[0]:.0f}–%{customdata[1]:.0f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            y=shown["location"], x=shown["median_rank"], mode="markers", name="median rank",
            marker={"color": "navy", "size": 9},
        ))
        fig.update_layout(
            height=max(400, 22 * len(shown)), xaxis_title="rank (1 = best)",
            legend={"orientation": "h", "y": -0.08}, margin={"l": 10},
        )
        st.plotly_chart(fig)
        st.caption(f"{n_combos} weight combinations, {len(stability)} countries with all selected criteria. "
                   "Showing the 30 best by median rank.")
        st.dataframe(
            stability, hide_index=True,
            column_config={
                "location": "Country", "continent": "Continent",
                "best_rank": st.column_config.NumberColumn("Best rank", format="%d"),
                "median_rank": st.column_config.NumberColumn("Median rank", format="%.0f"),
                "worst_rank": st.column_config.NumberColumn("Worst rank", format="%d"),
                "pct_in_top": st.column_config.ProgressColumn(
                    f"% of combos in top {top_n}", min_value=0, max_value=100, format="%.0f%%"),
            },
        )

# ---------------------------------------------------------------- 5. end date

with tabs[4]:
    st.markdown(
        "Pitfall 1: cumulative excess deaths keep growing. Countries that kept the virus out "
        "until vaccines arrived look best early on; some caught up later."
    )
    timeline_countries = st.multiselect(
        "Countries", all_countries,
        default=[c for c in (*DEFAULT_TIMELINE, *highlight) if c in all_countries],
        key="timeline_countries",
    )
    series = excess_timeseries(cached_daily(), timeline_countries)
    if series.empty:
        st.info("No excess-mortality data for these countries.")
    else:
        fig = px.line(
            series, x="date", y="excess_mortality_cumulative_per_million", color="location",
            labels={"excess_mortality_cumulative_per_million": "cumulative excess deaths per million",
                    "date": "", "location": "Country"},
        )
        for year_end in CUTOFFS:
            fig.add_vline(x=pd.Timestamp(year_end), line_dash="dot", line_color="grey")
        fig.update_layout(height=480)
        st.plotly_chart(fig)

    st.markdown(f"##### Rank on *{HEALTH_MEASURES[health_column].lower()}* by end date (current peer group)")
    rank_columns = {}
    for year_end in CUTOFFS:
        group, _, _ = peer_table(year_end, gdp_baseline, int(min_population), peer_continents, peer_countries)
        rank_columns[year_end[:4]] = group.set_index("location")[health_column].rank(method="min")
    ranks = pd.DataFrame(rank_columns)
    focus = ranks.loc[ranks.index.intersection(timeline_countries)]
    if focus.empty:
        st.info("None of the selected countries are in the current peer group.")
    else:
        st.dataframe(
            focus.sort_values(focus.columns[-1]),
            column_config={c: st.column_config.NumberColumn(f"Rank end {c}", format="%d") for c in ranks.columns},
        )
        st.caption("1 = fewest deaths. Empty = no recent excess-mortality data at that date.")

# ---------------------------------------------------------------- 6. vaccination speed

with tabs[5]:
    st.markdown(
        f"How quickly each country reached **{VAX_THRESHOLD:.0f}% fully vaccinated**, counted from "
        "the first dose outside trials (8 Dec 2020). Shown for context, not part of the score."
    )
    speed = peers.dropna(subset=["days_to_50pct_vax"]).sort_values("days_to_50pct_vax")
    never = sorted(set(peers["location"]) - set(speed["location"]))
    if not speed.empty:
        fig = px.bar(
            speed.head(40), x="days_to_50pct_vax", y="location", orientation="h", color="continent",
            labels={"days_to_50pct_vax": f"days to {VAX_THRESHOLD:.0f}% fully vaccinated", "location": ""},
        )
        fig.update_layout(height=max(400, 20 * min(len(speed), 40)), yaxis={"autorange": "reversed"})
        st.plotly_chart(fig)
        st.caption(f"Fastest 40 of {len(speed)} countries in the peer group.")
    if never:
        with st.expander(f"{len(never)} countries never reached {VAX_THRESHOLD:.0f}% (by end {cutoff[:4]}) or have no data"):
            st.write(", ".join(never))

    vax = vaccination_timeseries(cached_daily(), timeline_countries)
    if not vax.empty:
        fig = px.line(
            vax, x="date", y="people_fully_vaccinated_per_hundred", color="location",
            labels={"people_fully_vaccinated_per_hundred": "% fully vaccinated", "date": "", "location": "Country"},
        )
        fig.add_hline(y=VAX_THRESHOLD, line_dash="dot", line_color="grey")
        fig.update_layout(height=420)
        st.plotly_chart(fig)
        st.caption("Countries from the *End date matters* tab.")

# ---------------------------------------------------------------- 7. healthcare capacity

with tabs[6]:
    st.markdown(
        "Healthcare capacity **before** COVID (latest value 2015–2019, World Bank). It is not part of "
        "the score — more hospital beds isn't *coping better*, it's a starting point. The question here: "
        "**did countries with more capacity have better outcomes?**"
    )
    capacity_columns = list(CAPACITY_COLUMNS)
    outcome_columns = [health_column, *COST_CRITERIA.values()]
    corr, counts = capacity_correlations(peers, capacity_columns, outcome_columns)

    heat = corr.rename(index=CAPACITY_COLUMNS, columns=label)
    fig = px.imshow(
        heat, text_auto=".2f", color_continuous_scale="RdBu", zmin=-1, zmax=1, aspect="auto",
        labels={"color": "Spearman ρ"},
    )
    fig.update_layout(height=380, xaxis={"side": "top", "tickangle": -30}, margin={"t": 120})
    st.plotly_chart(fig)
    st.caption(
        f"Spearman rank correlation, {int(counts.min().min())}–{int(counts.max().max())} countries per cell. "
        "Every outcome is *lower is better*, so a **negative (red) value** means more capacity went with a "
        "better outcome. Beware: richer countries have more capacity *and* older populations, better death "
        "registration and more money for support — correlation is not causation."
    )

    c1, c2 = st.columns(2)
    capacity_column = c1.selectbox("Capacity measure", capacity_columns, format_func=CAPACITY_COLUMNS.get)
    outcome_column = c2.selectbox("Outcome", outcome_columns, format_func=label)
    pair = peers.dropna(subset=[capacity_column, outcome_column])
    if len(pair) < 3:
        st.info("Too few countries have both values.")
    else:
        rho = pair[[capacity_column, outcome_column]].corr(method="spearman").iloc[0, 1]
        fig = px.scatter(
            pair, x=capacity_column, y=outcome_column, color="continent", hover_name="location",
            text=[loc if loc in highlight else "" for loc in pair["location"]],
            log_x=capacity_column == "health_spending_per_capita_usd", labels=COLUMN_LABELS,
            title=f"Spearman ρ = {rho:.2f}  ({len(pair)} countries)",
        )
        fig.update_traces(textposition="top center")
        fig.update_layout(height=500)
        st.plotly_chart(fig)

    with st.expander("Capacity per country"):
        st.dataframe(
            peers[["location", "continent", *capacity_columns]].sort_values("location"),
            hide_index=True,
            column_config={
                "location": "Country", "continent": "Continent",
                **{c: st.column_config.NumberColumn(CAPACITY_COLUMNS[c], format="%.1f") for c in capacity_columns},
            },
        )

# ---------------------------------------------------------------- 8. data quality

with tabs[7]:
    st.markdown(
        "Pitfall 3: where excess deaths are many times the reported COVID deaths, the official "
        "figures can't be trusted — and countries without death registration are missing entirely."
    )
    quality = peers.dropna(subset=["excess_vs_reported"]).sort_values("excess_vs_reported", ascending=False)
    st.dataframe(
        quality[["location", "continent", "excess_pm", "reported_pm", "excess_vs_reported"]],
        hide_index=True,
        column_config={
            "location": "Country", "continent": "Continent",
            "excess_pm": st.column_config.NumberColumn(label("excess_pm"), format="%.0f"),
            "reported_pm": st.column_config.NumberColumn(label("reported_pm"), format="%.0f"),
            "excess_vs_reported": st.column_config.NumberColumn(label("excess_vs_reported"), format="%.1f×"),
        },
    )
    if not quality.empty:
        st.caption(f"Median ratio in this group: {quality['excess_vs_reported'].median():.2f}×.")

    st.markdown("##### Missing data in the current peer group")
    gaps = {
        f"No recent excess mortality (end {cutoff[:4]})": peers.loc[peers["excess_pm"].isna(), "location"],
        f"No GDP loss ({baseline_label})": peers.loc[peers["gdp_loss_pct"].isna(), "location"],
        "No unemployment data": peers.loc[peers["unemployment_rise_pp"].isna(), "location"],
        "No school-closure data": peers.loc[peers["school_weeks_full"].isna(), "location"],
        "No stringency index": peers.loc[peers["avg_stringency"].isna(), "location"],
        "No life-expectancy data": peers.loc[peers["life_expectancy_drop_years"].isna(), "location"],
        "No GDP recovery data": peers.loc[peers["gdp_years_below_2019"].isna(), "location"],
        "No healthcare-capacity data": peers.loc[peers[capacity_columns].isna().all(axis=1), "location"],
    }
    for title, names in gaps.items():
        with st.expander(f"{title}: {len(names)}"):
            st.write(", ".join(sorted(names)) or "—")
