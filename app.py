import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Education vs GDP", layout="wide")

st.markdown(
    """<style>
    #MainMenu {visibility: hidden;}
    header [data-testid="stToolbar"] {visibility: hidden;}
    .viewerBadge_container__r5tak {display: none;}
    [data-testid="stDecoration"] {display: none;}
    </style>""",
    unsafe_allow_html=True,
)

DATA_DIR = "."
AVAILABLE_YEARS = [1990, 1995, 2000, 2005, 2010, 2015, 2020]


@st.cache_data
def load_all_data():
    schooling = pd.read_csv(f"{DATA_DIR}/mean_years_schooling.csv")
    gdp = pd.read_csv(f"{DATA_DIR}/gdp_per_capita.csv")
    pop = pd.read_csv(f"{DATA_DIR}/population.csv")

    s = schooling[schooling["Year"].isin(AVAILABLE_YEARS)].dropna(subset=["Code"]).copy()
    g = gdp[gdp["Year"].isin(AVAILABLE_YEARS)].dropna(subset=["Code"]).copy()
    p = pop[pop["Year"].isin(AVAILABLE_YEARS)].dropna(subset=["Code"])[["Code", "Year", "Population"]].copy()

    df = s.merge(g, on=["Code", "Year"], how="inner").merge(p, on=["Code", "Year"], how="left")
    df = df.rename(columns={
        "Entity_x": "country",
        "Code": "iso3",
        "Average years of schooling": "schooling_years",
        "GDP per capita": "gdp_per_capita",
        "World region according to OWID": "region",
    })
    return df[["country", "iso3", "Year", "schooling_years", "gdp_per_capita", "region", "Population"]].dropna()


all_data = load_all_data()

REGION_COLORS = {
    region: color
    for region, color in zip(
        sorted(all_data["region"].unique()),
        px.colors.qualitative.Safe,
    )
}
REGION_COLORS["Oceania"] = "rgb(255, 140, 0)"

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("Filters")
selected_year = st.sidebar.selectbox(
    "Year",
    options=AVAILABLE_YEARS[::-1],
    index=0,
)

df = all_data[all_data["Year"] == selected_year].copy()

# ── Session state for selection ───────────────────────────────────────────────
if "selected_iso3" not in st.session_state:
    st.session_state.selected_iso3 = None

# Clear selection if selected country has no data in the new year
if st.session_state.selected_iso3 and st.session_state.selected_iso3 not in df["iso3"].values:
    st.session_state.selected_iso3 = None


def make_scatter(selected_iso3):
    if selected_iso3:
        df_sel = df[df["iso3"] == selected_iso3]
        df_rest = df[df["iso3"] != selected_iso3]
    else:
        df_sel = df
        df_rest = pd.DataFrame()

    fig = go.Figure()

    max_pop = df["Population"].max()

    def bubble_sizes(population_series):
        return (population_series / max_pop).pow(0.5) * 60 + 5

    if not df_rest.empty:
        fig.add_trace(go.Scatter(
            x=df_rest["schooling_years"],
            y=df_rest["gdp_per_capita"],
            mode="markers",
            marker=dict(color="lightgrey", size=bubble_sizes(df_rest["Population"]), opacity=0.4),
            text=df_rest["country"],
            customdata=df_rest["iso3"],
            hovertemplate="<b>%{text}</b><br>Schooling: %{x:.1f} yrs<br>GDP/capita: $%{y:,.0f}<extra></extra>",
            showlegend=False,
        ))

    for region, group in (df_sel if not selected_iso3 else df_sel.assign(region=df_sel["region"])).groupby("region") if not selected_iso3 else [(df_sel.iloc[0]["region"], df_sel)]:
        fig.add_trace(go.Scatter(
            x=group["schooling_years"],
            y=group["gdp_per_capita"],
            mode="markers",
            marker=dict(
                color=REGION_COLORS.get(region, "steelblue"),
                size=bubble_sizes(group["Population"]),
                line=dict(width=1.5 if selected_iso3 else 0, color="black"),
            ),
            name=region,
            text=group["country"],
            customdata=group["iso3"],
            hovertemplate="<b>%{text}</b><br>Schooling: %{x:.1f} yrs<br>GDP/capita: $%{y:,.0f}<br>Population: %{meta:,}<extra></extra>",
            meta=group["Population"],
        ))

    fig.update_layout(
        xaxis=dict(title="Average Years of Schooling", title_font=dict(size=32), tickfont=dict(size=24), fixedrange=True),
        yaxis=dict(
            title="GDP per Capita (USD)", title_font=dict(size=24),
            fixedrange=True,
            tickformat="$,.0f",
            tickfont=dict(size=20),
        ),
        margin=dict(l=70, r=0, t=10, b=0),
        height=420,
        legend=dict(title=dict(text="Region", font=dict(size=24)), font=dict(size=18), orientation="v"),
        clickmode="event+select",
    )
    return fig


def make_choropleth(column, title, colorscale, selected_iso3):
    fig = go.Figure()

    if selected_iso3:
        df_rest = df[df["iso3"] != selected_iso3]
        df_sel = df[df["iso3"] == selected_iso3]

        # Grey trace for all unselected countries
        fig.add_trace(go.Choropleth(
            locations=df_rest["iso3"],
            z=[1] * len(df_rest),
            colorscale=[[0, "lightgrey"], [1, "lightgrey"]],
            showscale=False,
            hovertemplate="<b>%{customdata[0]}</b><extra></extra>",
            customdata=df_rest[["iso3"]].values,
            marker_line_color="white",
            marker_line_width=0.5,
        ))

        # Coloured trace for selected country
        vmin, vmax = df[column].min(), df[column].max()
        fig.add_trace(go.Choropleth(
            locations=df_sel["iso3"],
            z=df_sel[column],
            zmin=vmin,
            zmax=vmax,
            colorscale=colorscale,
            colorbar=dict(title=title),
            hovertemplate="<b>%{customdata[0]}</b><br>" + title + ": %{z:,.1f}<extra></extra>",
            customdata=df_sel[["iso3"]].values,
            marker_line_color="black",
            marker_line_width=1.5,
        ))
    else:
        fig.add_trace(go.Choropleth(
            locations=df["iso3"],
            z=df[column],
            colorscale=colorscale,
            colorbar=dict(title=title),
            hovertemplate="<b>%{customdata[0]}</b><br>" + title + ": %{z:,.1f}<extra></extra>",
            customdata=df[["iso3"]].values,
            marker_line_color="white",
            marker_line_width=0.5,
        ))

    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
        margin=dict(l=0, r=0, t=10, b=0),
        height=380,
        clickmode="event+select",
    )
    return fig


# ── Header ────────────────────────────────────────────────────────────────────
st.title(f"Education and GDP across the world ({selected_year})")
st.markdown(
    "<p style='font-size: 1.4rem;'>Do countries with higher levels of education tend to have higher GDP per capita?<br>"
    "Click any country on a chart to highlight it across all three views. "
    "Click again to deselect.</p>",
    unsafe_allow_html=True,
)
st.caption(
    "Data sources: "
    "[Average years of schooling](https://ourworldindata.org/grapher/mean-years-of-schooling-long-run) · "
    "[GDP per capita](https://ourworldindata.org/grapher/gdp-per-capita-worldbank) — Our World in Data"
)

if st.session_state.selected_iso3:
    country_name = df[df["iso3"] == st.session_state.selected_iso3]["country"].values
    label = country_name[0] if len(country_name) else st.session_state.selected_iso3
    st.markdown(
        """<style>div[data-testid="stButton"] button {font-size: 1.1rem; padding: 0.4rem 1rem;}</style>""",
        unsafe_allow_html=True,
    )
    col_clear, _ = st.columns([1, 5])
    with col_clear:
        if st.button(f"Clear selection: {label}"):
            st.session_state.selected_iso3 = None
            st.rerun()

# ── Country detail card ───────────────────────────────────────────────────────
if st.session_state.selected_iso3:
    row = df[df["iso3"] == st.session_state.selected_iso3]
    if not row.empty:
        r = row.iloc[0]
        st.subheader(f"{r['country']} — Detail")
        m1, m2, m3 = st.columns(3)
        m1.metric("Region", r["region"])
        m2.metric("Avg Years of Schooling", f"{r['schooling_years']:.1f} yrs")
        m3.metric("GDP per Capita", f"${r['gdp_per_capita']:,.0f}")

st.divider()

# ── Scatter plot ──────────────────────────────────────────────────────────────
st.subheader("Schooling vs GDP per Capita")
scatter_fig = make_scatter(st.session_state.selected_iso3)
scatter_event = st.plotly_chart(scatter_fig, on_select="rerun", key="scatter", width="stretch")

if scatter_event and scatter_event.selection and scatter_event.selection.points:
    pt = scatter_event.selection.points[0]
    clicked_iso3 = pt.get("customdata")
    if clicked_iso3:
        new_sel = None if clicked_iso3 == st.session_state.selected_iso3 else clicked_iso3
        if new_sel != st.session_state.selected_iso3:
            st.session_state.selected_iso3 = new_sel
            st.rerun()

st.divider()

# ── Choropleth maps ───────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Average Years of Schooling")
    map1_fig = make_choropleth("schooling_years", "Yrs of Schooling", "YlGnBu", st.session_state.selected_iso3)
    map1_event = st.plotly_chart(map1_fig, on_select="rerun", key="map_schooling", width="stretch")

    if map1_event and map1_event.selection and map1_event.selection.points:
        pt = map1_event.selection.points[0]
        clicked_iso3 = pt.get("customdata", [None])[0] if pt.get("customdata") else None
        if clicked_iso3:
            new_sel = None if clicked_iso3 == st.session_state.selected_iso3 else clicked_iso3
            if new_sel != st.session_state.selected_iso3:
                st.session_state.selected_iso3 = new_sel
                st.rerun()

with col2:
    st.subheader("GDP per Capita (USD)")
    map2_fig = make_choropleth("gdp_per_capita", "GDP/capita", "YlOrRd", st.session_state.selected_iso3)
    map2_event = st.plotly_chart(map2_fig, on_select="rerun", key="map_gdp", width="stretch")

    if map2_event and map2_event.selection and map2_event.selection.points:
        pt = map2_event.selection.points[0]
        clicked_iso3 = pt.get("customdata", [None])[0] if pt.get("customdata") else None
        if clicked_iso3:
            new_sel = None if clicked_iso3 == st.session_state.selected_iso3 else clicked_iso3
            if new_sel != st.session_state.selected_iso3:
                st.session_state.selected_iso3 = new_sel
                st.rerun()

