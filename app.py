"""Exploration dashboard for the OWID COVID-19 dataset."""

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

from data import (
    COMPARE_METRICS,
    DEMOGRAPHIC_COLUMNS,
    METRIC_GROUPS,
    SPARSE_CATEGORIES,
    country_snapshot,
    filter_data,
    has_data,
    latest_doses_by_vaccine,
    latest_value,
    load_data,
    load_vaccine_cfr_summary,
    load_vaccine_manufacturer_data,
    split_locations,
    vaccination_outcome_snapshot,
)

def _short_list(names: list[str], limit: int = 6) -> str:
    if len(names) <= limit:
        return ", ".join(names)
    shown = ", ".join(names[:limit])
    return f"{shown}, and {len(names) - limit} more"


st.set_page_config(
    page_title="COVID-19 explorer",
    page_icon=":material/coronavirus:",
    layout="wide",
)

df = load_data()
countries_df, aggregates = split_locations(df)
min_date = df["date"].min().date()
max_date = df["date"].max().date()

"# COVID-19 data explorer"
st.caption("Explore cases, deaths, vaccinations, and related metrics from the Our World in Data COVID-19 dataset.")

with st.sidebar:
    st.markdown("### Filters")

    location_type = st.segmented_control(
        "Location type",
        ["Countries", "Regions & aggregates"],
        default="Countries",
    )

    if location_type == "Countries":
        continents = ["All continents"] + sorted(countries_df["continent"].unique().tolist())
        continent = st.selectbox("Continent", continents)
        if continent == "All continents":
            available_locations = sorted(countries_df["location"].tolist())
        else:
            available_locations = sorted(
                countries_df.loc[countries_df["continent"] == continent, "location"].tolist()
            )
        default_locations = [loc for loc in ("United States", "Germany") if loc in available_locations]
        selected_locations = st.multiselect(
            "Countries", available_locations, default=default_locations or available_locations[:1]
        )
    else:
        continent = None
        selected_locations = st.multiselect(
            "Regions & aggregates", aggregates, default=["World"] if "World" in aggregates else aggregates[:1]
        )

    start_date, end_date = st.slider(
        "Date range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
    )

    category = st.selectbox("Metric category", list(METRIC_GROUPS))
    metric_options = METRIC_GROUPS[category]
    metric = st.selectbox(
        "Metric", list(metric_options), format_func=lambda col: metric_options[col]
    )

    if category in SPARSE_CATEGORIES:
        st.caption(
            "This category is reported by only a small share of location-days in the "
            "dataset, so many selections will show no data."
        )

if not selected_locations:
    st.warning("Select at least one location in the sidebar.", icon=":material/warning:")
    st.stop()

metric_label = metric_options[metric]
columns_needed = sorted({metric, *COMPARE_METRICS})
filtered = filter_data(df, selected_locations, start_date, end_date, columns_needed)

continent_names = set(countries_df["continent"].unique())
if location_type == "Countries":
    # Zoom to exactly the selected countries, not the whole continent filter.
    region_continents = None
    map_locations = selected_locations
else:
    map_locations = None
    region_continents = [loc for loc in selected_locations if loc in continent_names] or None

trends_tab, compare_tab, summary_tab, map_tab, vaccine_tab, brands_tab = st.tabs(
    ["Trends", "Compare", "Summary", "Map", "Vaccine effect", "Vaccine brands"]
)

with trends_tab:
    f"### {metric_label} over time"
    if not has_data(filtered, metric):
        st.info(
            f"No {metric_label.lower()} data available for the selected locations and date range.",
            icon=":material/info:",
        )
    else:
        chart = (
            alt.Chart(filtered.dropna(subset=[metric]))
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y(f"{metric}:Q", title=metric_label),
                color=alt.Color("location:N", title="Location"),
                tooltip=[
                    alt.Tooltip("location:N", title="Location"),
                    alt.Tooltip("date:T", title="Date"),
                    alt.Tooltip(f"{metric}:Q", title=metric_label),
                ],
            )
            .configure_legend(orient="bottom")
        )
        st.altair_chart(chart, width="stretch")

with compare_tab:
    "### Side-by-side comparison"

    missing_for_metric = [
        loc for loc in selected_locations if not has_data(filtered[filtered["location"] == loc], metric)
    ]
    if missing_for_metric:
        st.caption(f"No {metric_label.lower()} data for: {', '.join(missing_for_metric)}")

    rows = []
    for loc in selected_locations:
        loc_df = filtered[filtered["location"] == loc]
        row = {"Location": loc}
        for col, label in COMPARE_METRICS.items():
            row[label] = latest_value(loc_df, loc, col)
        rows.append(row)

    st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        column_config={
            label: st.column_config.NumberColumn(label, format="%.1f")
            for label in COMPARE_METRICS.values()
        },
    )

    with st.expander("Raw filtered data"):
        st.dataframe(filtered.rename(columns={metric: metric_label}), hide_index=True, width="stretch")

with summary_tab:
    focus_location = st.selectbox("Focus location", selected_locations)
    focus_df = filtered[filtered["location"] == focus_location]

    "#### Latest figures"
    with st.container(horizontal=True, gap="medium"):
        for col, label in COMPARE_METRICS.items():
            value = latest_value(focus_df, focus_location, col)
            st.metric(label, f"{value:,.1f}" if value is not None else "—")

    "#### Location profile"
    profile_row = df.loc[df["location"] == focus_location, list(DEMOGRAPHIC_COLUMNS)].iloc[0]
    with st.container(horizontal=True, gap="medium"):
        for col, label in DEMOGRAPHIC_COLUMNS.items():
            value = profile_row[col]
            st.metric(label, f"{value:,.1f}" if pd.notna(value) else "—")

with map_tab:
    f"### {metric_label} by country"

    zoomed_to = map_locations or region_continents
    if zoomed_to:
        st.caption(f"Zoomed to {_short_list(zoomed_to)} - latest reported value per country within the selected date range.")
    else:
        st.caption(
            "Shows every country's latest reported value within the selected date range "
            "- not limited to the locations chosen in the sidebar."
        )

    snapshot = country_snapshot(
        df, metric, start_date, end_date, continents=region_continents, locations=map_locations
    )
    if snapshot.empty:
        st.info(
            f"No {metric_label.lower()} data available for this selection and date range.",
            icon=":material/info:",
        )
    else:
        fig = px.choropleth(
            snapshot,
            locations="iso_code",
            locationmode="ISO-3",
            color=metric,
            hover_name="location",
            color_continuous_scale="YlOrRd",
            labels={metric: metric_label},
        )
        fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0})
        if zoomed_to:
            fig.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig, width="stretch")

with vaccine_tab:
    "### Vaccination rate vs. deaths, across countries"
    st.caption(
        "Each point is one country's latest simultaneous reading of fully-vaccinated rate "
        "and cumulative deaths per million, within the selected date range. This is a "
        "cross-country correlation, not a controlled comparison - differences in age "
        "structure, healthcare capacity, and reporting quality between countries can "
        "produce or mask patterns that have nothing to do with vaccines."
    )

    scatter_df = vaccination_outcome_snapshot(df, start_date, end_date)
    if scatter_df.empty:
        st.info(
            "No vaccination and death data available for this date range.",
            icon=":material/info:",
        )
    else:
        points = alt.Chart(scatter_df).mark_circle(opacity=0.7).encode(
            x=alt.X("people_fully_vaccinated_per_hundred:Q", title="Fully vaccinated (%)"),
            y=alt.Y("total_deaths_per_million:Q", title="Cumulative deaths per million"),
            color=alt.Color("continent:N", title="Continent"),
            size=alt.Size("population:Q", title="Population", legend=None),
            tooltip=[
                alt.Tooltip("location:N", title="Country"),
                alt.Tooltip("people_fully_vaccinated_per_hundred:Q", title="Fully vaccinated (%)"),
                alt.Tooltip("total_deaths_per_million:Q", title="Deaths per million"),
            ],
        )
        trend = points.transform_regression(
            "people_fully_vaccinated_per_hundred", "total_deaths_per_million"
        ).mark_line(color="black", strokeDash=[4, 2])
        st.altair_chart((points + trend).configure_legend(orient="bottom"), width="stretch")

    "### Before vs. after reaching 10% fully vaccinated"
    st.caption(
        "Case-fatality rate (deaths / confirmed cases) for 7 locations, comparing the period "
        "before vs. after each one crossed 10% full vaccination coverage. This within-country "
        "before/after comparison controls for each country's own demographics and healthcare "
        "system, but is still confounded by variant-severity shifts (e.g. Omicron) and "
        "treatment improvements happening in the same window - see "
        "covid_vaccine_analysis_summary.md for the full caveats."
    )

    cfr_df = load_vaccine_cfr_summary()
    cfr_long = cfr_df.melt(
        id_vars="location",
        value_vars=["CFR_percent_before_10pct_vaccinated", "CFR_percent_after_10pct_vaccinated"],
        var_name="period",
        value_name="cfr_percent",
    )
    cfr_long["period"] = cfr_long["period"].map(
        {
            "CFR_percent_before_10pct_vaccinated": "Before 10% vaccinated",
            "CFR_percent_after_10pct_vaccinated": "After 10% vaccinated",
        }
    )

    bar_chart = (
        alt.Chart(cfr_long)
        .mark_bar()
        .encode(
            x=alt.X("location:N", title=None),
            xOffset=alt.XOffset("period:N", sort=["Before 10% vaccinated", "After 10% vaccinated"]),
            y=alt.Y("cfr_percent:Q", title="Case-fatality rate (%)"),
            color=alt.Color(
                "period:N", title=None, sort=["Before 10% vaccinated", "After 10% vaccinated"]
            ),
            tooltip=[
                alt.Tooltip("location:N", title="Location"),
                alt.Tooltip("period:N", title="Period"),
                alt.Tooltip("cfr_percent:Q", title="CFR (%)"),
            ],
        )
        .configure_legend(orient="bottom")
    )
    st.altair_chart(bar_chart, width="stretch")

    with st.expander("Relative change per location"):
        st.dataframe(
            cfr_df[
                ["location", "date_reached_10pct_fully_vaccinated", "CFR_relative_change_pct"]
            ],
            hide_index=True,
            width="stretch",
            column_config={
                "CFR_relative_change_pct": st.column_config.NumberColumn(
                    "CFR change", format="%.1f%%"
                ),
            },
        )

with brands_tab:
    "### Doses administered by vaccine brand"
    st.caption(
        "OWID's by-manufacturer dataset - a different, smaller set of ~44 mostly-European "
        "locations (plus the US, Canada, Japan, South Korea, and a few others), 2020-12 to "
        "2024-08. Not part of the main OWID dataset used elsewhere in this app, so it isn't "
        "limited to the locations selected in the sidebar."
    )

    brand_df = load_vaccine_manufacturer_data()
    brand_locations = sorted(brand_df["location"].unique())
    default_brand_location = next(
        (loc for loc in selected_locations if loc in brand_locations),
        "United States" if "United States" in brand_locations else brand_locations[0],
    )
    brand_location = st.selectbox(
        "Location", brand_locations, index=brand_locations.index(default_brand_location)
    )

    "#### Cumulative doses over time"
    location_brand_df = brand_df[brand_df["location"] == brand_location]
    area_chart = (
        alt.Chart(location_brand_df)
        .mark_area()
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("total_vaccinations:Q", title="Cumulative doses", stack=True),
            color=alt.Color("vaccine:N", title="Vaccine"),
            tooltip=[
                alt.Tooltip("vaccine:N", title="Vaccine"),
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("total_vaccinations:Q", title="Cumulative doses"),
            ],
        )
        .configure_legend(orient="bottom")
    )
    st.altair_chart(area_chart, width="stretch")

    "#### Total doses by brand, across all reporting locations"
    st.caption("Summed across the ~44 locations above - not a global total.")
    brand_totals = latest_doses_by_vaccine(brand_df)
    totals_chart = (
        alt.Chart(brand_totals)
        .mark_bar()
        .encode(
            x=alt.X("total_vaccinations:Q", title="Total doses administered"),
            y=alt.Y("vaccine:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("vaccine:N", title="Vaccine"),
                alt.Tooltip("total_vaccinations:Q", title="Total doses"),
            ],
        )
    )
    st.altair_chart(totals_chart, width="stretch")
