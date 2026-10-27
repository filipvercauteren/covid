"""Animated world heatmap of COVID-19 deaths - OWID dataset."""

import numpy as np
import plotly.express as px
import streamlit as st

from data import (
    ANIMATION_FREQUENCIES,
    ANIMATION_METRICS,
    animated_metric_snapshot,
    load_data,
    split_locations,
)


def _short_list(names: list[str], limit: int = 6) -> str:
    if len(names) <= limit:
        return ", ".join(names)
    shown = ", ".join(names[:limit])
    return f"{shown}, and {len(names) - limit} more"


def _log_color_ticks(max_value: float) -> tuple[list[float], list[str]]:
    """Round-number tick candidates (in real units) for a log1p color axis,
    trimmed to the metric's actual range, for a readable colorbar."""
    candidates = [0, 1, 3, 10, 30, 100, 300, 1_000, 3_000, 10_000, 30_000, 100_000, 300_000, 1_000_000, 3_000_000]
    ticks = [v for v in candidates if v <= max_value] or [0, max_value]
    return [np.log1p(v) for v in ticks], [f"{v:,.0f}" for v in ticks]


st.set_page_config(
    page_title="COVID-19 death animation",
    page_icon=":material/coronavirus:",
    layout="wide",
)

df = load_data()
countries_df, aggregates = split_locations(df)

"# Deaths over time, animated across the world"
st.caption(
    "Plays through the whole pandemic from first reported data to the latest, country by "
    "country. Press play on the map below."
)

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
        selected_locations = st.multiselect(
            "Regions & aggregates", aggregates, default=["World"] if "World" in aggregates else aggregates[:1]
        )

continent_names = set(countries_df["continent"].unique())
if location_type == "Countries":
    # Zoom to exactly the selected countries, not the whole continent filter.
    region_continents = None
    map_locations = selected_locations
else:
    map_locations = None
    region_continents = [loc for loc in selected_locations if loc in continent_names] or None

with st.container(horizontal=True, gap="medium"):
    anim_metric = st.selectbox(
        "Metric to animate",
        list(ANIMATION_METRICS),
        format_func=lambda col: ANIMATION_METRICS[col],
        key="anim_metric",
    )
    freq_label = st.selectbox("Step size", list(ANIMATION_FREQUENCIES), key="anim_freq")
    speed_ms = st.slider(
        "Frame speed (ms)", min_value=10, max_value=1000, value=250, step=10, key="anim_speed"
    )

show_world = st.checkbox(
    "Show whole world", key="anim_world", help="Ignore the sidebar's location filter for this map."
)
anim_locations = None if show_world else map_locations
anim_continents = None if show_world else region_continents

zoomed_to = anim_locations or anim_continents
if zoomed_to:
    st.caption(f"Zoomed to {_short_list(zoomed_to)}.")
else:
    st.caption("Shows every country worldwide.")

anim_label = ANIMATION_METRICS[anim_metric]
anim_snapshot = animated_metric_snapshot(
    df,
    anim_metric,
    freq=ANIMATION_FREQUENCIES[freq_label],
    continents=anim_continents,
    locations=anim_locations,
)
if anim_snapshot.empty:
    st.info(
        f"No {anim_label.lower()} data available for this selection.",
        icon=":material/info:",
    )
else:
    # Log-scale the color so the scale isn't dominated by a handful of huge
    # countries - without it, cumulative counts are so skewed that most of
    # the pandemic looks pale and everything jumps to red only right at the
    # end. This makes the ramp to red faster and the animation feel punchier.
    color_col = "_color_value"
    anim_snapshot[color_col] = np.log1p(anim_snapshot[anim_metric].clip(lower=0))
    tickvals, ticktext = _log_color_ticks(anim_snapshot[anim_metric].max())

    fig = px.choropleth(
        anim_snapshot,
        locations="iso_code",
        locationmode="ISO-3",
        color=color_col,
        hover_name="location",
        hover_data={anim_metric: ":,.0f", color_col: False, "iso_code": False},
        animation_frame="period",
        color_continuous_scale="YlOrRd",
        range_color=(0, anim_snapshot[color_col].max()),
        labels={anim_metric: anim_label, "period": "Date"},
    )
    fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0})
    fig.update_coloraxes(
        colorbar_title=anim_label, colorbar_tickvals=tickvals, colorbar_ticktext=ticktext
    )
    if zoomed_to:
        fig.update_geos(fitbounds="locations", visible=False)
    if fig.layout.updatemenus:
        play_button = fig.layout.updatemenus[0].buttons[0]
        play_button.args[1]["frame"]["duration"] = speed_ms
        play_button.args[1]["transition"]["duration"] = min(speed_ms, 200)
    st.plotly_chart(fig, width="stretch")
