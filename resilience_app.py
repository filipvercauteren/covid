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
    COLUMN_LABELS,
    CRITERIA_LABELS,
    CUTOFFS,
    DB_PATH,
    HEALTH_MEASURES,
    VAX_THRESHOLD,
    add_age_adjusted_excess,
    country_metrics,
    criterion_columns,
    excess_timeseries,
    load_daily,
    load_gdp_loss,
    rank_stability,
    score_countries,
    select_peers,
    vaccination_timeseries,
)

DEFAULT_HIGHLIGHT = ("Belgium",)
DEFAULT_PEERS = ("Belgium", "Netherlands", "Germany", "France", "Denmark", "Sweden", "Norway",
                 "United Kingdom", "Austria", "Switzerland", "Italy", "Spain")
DEFAULT_TIMELINE = ("New Zealand", "Australia", "Japan", "Belgium", "Sweden", "Denmark")


# ---------------------------------------------------------------- data (cached)

@st.cache_data(show_spinner="Loading covid-combo.db…")
def cached_daily() -> pd.DataFrame:
    return load_daily(DB_PATH)


@st.cache_data(show_spinner=False)
def cached_metrics(cutoff: str) -> pd.DataFrame:
    return country_metrics(cached_daily(), load_gdp_loss(DB_PATH), cutoff)


@st.cache_data(show_spinner=False)
def peer_table(
    cutoff: str, min_population: int, continents: tuple[str, ...], countries: tuple[str, ...]
) -> tuple[pd.DataFrame, float, float]:
    """Metrics for the peer group. The age fit uses every country above the
    population threshold (more stable than fitting on a small peer group)."""
    metrics = select_peers(cached_metrics(cutoff), min_population)
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
    "Lower is better on every criterion. Data: OWID, OxCGRT (via OWID), World Bank — see `sources.md`."
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

peers, age_slope, age_corr = peer_table(cutoff, int(min_population), peer_continents, peer_countries)

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
| | Hospital overload | ⚠️ shown, not scored — ICU data for ~40 countries | `icu_patients_per_million` |
| | Years of life lost | ❌ not available | — |
| **Economy** | GDP loss 2020–23 vs. 2015–19 trend | ✅ | `gdp_covid_loss` (World Bank) |
| | Unemployment, debt, support costs | ❌ not available | — |
| **Society** | Restrictions (stringency) | ✅ "freedom" criterion | `stringency_index` (OxCGRT) |
| | School closures, mental health | ❌ not available | — |
| **Resilience** | Vaccination speed | ✅ shown, not scored | `people_fully_vaccinated_per_hundred` |
"""
    )
    st.markdown("##### Coverage in the current peer group")
    cols = st.columns(5)
    cols[0].metric("Countries", len(peers))
    cols[1].metric("With excess mortality", int(peers["excess_pm"].notna().sum()))
    cols[2].metric("With GDP loss", int(peers["gdp_loss_pct"].notna().sum()))
    cols[3].metric("With stringency", int(peers["avg_stringency"].notna().sum()))
    cols[4].metric("With ICU data", int(peers["peak_icu_pm"].notna().sum()))

    with st.expander("Methodological pitfalls that change the ranking"):
        st.markdown(
            """
1. **The end date matters** — see *End date matters*. Use the sidebar slider.
2. **Compare like with like** — islands and young or wealthy countries have built-in advantages.
   Use *Compare with* to pick a peer group.
3. **Data quality** — countries with poor death registration are missing from excess mortality,
   or look better than reality. See *Data quality*.
4. **Weighting** — the weights largely decide the winner. See *Weight sensitivity*.

Also: GDP loss includes non-COVID shocks (energy crisis 2022, wars, oil booms), and stringency
measures rules on paper, not how people behaved.
"""
        )

# ---------------------------------------------------------------- 2. scatter

with tabs[1]:
    c1, c2, c3 = st.columns([2, 2, 1])
    x_column = c1.radio(
        "Cost on the x axis", ["gdp_loss_pct", "avg_stringency"], format_func=label, horizontal=True
    )
    color_column = "avg_stringency" if x_column == "gdp_loss_pct" else "gdp_loss_pct"
    max_gdp_loss = c2.slider(
        "Hide countries with |GDP loss| above (%)", 5, 50, 25,
        help="Very large values are mostly other shocks (oil booms, wars, tourism collapse).",
    )
    label_all = c3.toggle("Label all", value=len(peers) <= 30)

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
            f"Deaths measured up to end {cutoff[:4]}; GDP loss always 2020–23; stringency 2020–22."
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
    w1, w2, w3 = st.columns(3)
    weights = {
        "health": w1.slider(CRITERIA_LABELS["health"], 0, 10, 5),
        "economy": w2.slider(CRITERIA_LABELS["economy"], 0, 10, 3),
        "freedom": w3.slider(CRITERIA_LABELS["freedom"], 0, 10, 2),
    }

    if sum(weights.values()) == 0:
        st.warning("Give at least one criterion a weight above 0.")
    else:
        total = sum(weights.values())
        st.caption(" · ".join(f"{CRITERIA_LABELS[k]} {100 * w / total:.0f}%" for k, w in weights.items()))
        scored, missing = score_countries(peers, health_column, weights)
        columns = criterion_columns(health_column)

        table = scored[[
            "rank", "location", "continent", "score",
            columns["health"], "gdp_loss_pct", "avg_stringency", "pct_fully_vax", "peak_icu_pm",
        ]]
        st.dataframe(
            table,
            hide_index=True,
            height=min(38 * (len(table) + 1), 700),
            column_config={
                "rank": st.column_config.NumberColumn("#", format="%d", width="small"),
                "location": "Country",
                "continent": "Continent",
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                columns["health"]: st.column_config.NumberColumn(label(columns["health"]), format="%.0f"),
                "gdp_loss_pct": st.column_config.NumberColumn(label("gdp_loss_pct"), format="%.1f"),
                "avg_stringency": st.column_config.NumberColumn(label("avg_stringency"), format="%.1f"),
                "pct_fully_vax": st.column_config.NumberColumn(label("pct_fully_vax"), format="%.0f"),
                "peak_icu_pm": st.column_config.NumberColumn(label("peak_icu_pm"), format="%.0f"),
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
    top_n = st.slider("Count as 'top' when ranked in the first", 3, 25, 10)
    stability, n_combos = rank_stability(peers, health_column, step=0.1, top_n=top_n)

    if stability.empty:
        st.info("No countries have all three criteria.")
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
        st.caption(f"{n_combos} weight combinations, {len(stability)} countries with all three criteria. "
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
        group, _, _ = peer_table(year_end, int(min_population), peer_continents, peer_countries)
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

# ---------------------------------------------------------------- 7. data quality

with tabs[6]:
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
        "No GDP loss": peers.loc[peers["gdp_loss_pct"].isna(), "location"],
        "No stringency index": peers.loc[peers["avg_stringency"].isna(), "location"],
    }
    for title, names in gaps.items():
        with st.expander(f"{title}: {len(names)}"):
            st.write(", ".join(sorted(names)) or "—")
