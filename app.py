"""
CaneCycle - Feature 2: Residue Quantification Dashboard
----------------------------------------------------------
A simple local browser viewer for residue_quantities.csv.
This does NOT change any of the underlying calculation logic --
it just visualizes the output of 03_residue_quantification.py.

Run from the repo root (the folder this file sits in):
    streamlit run app.py

It will open automatically in your browser at http://localhost:8501
"""

import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="CaneCycle - Residue Quantification", layout="wide")

DATA_PATH = Path(__file__).resolve().parent / "data" / "residue_quantities.csv"

st.title("🌾 CaneCycle — Feature 2: Residue Quantification")
st.caption("RPR-based conversion of harvested area into residue tonnage, by type.")

if not DATA_PATH.exists():
    st.error(
        f"Could not find {DATA_PATH}.\n\n"
        "Run 01_generate_mock_data.py and 03_residue_quantification.py first, "
        "then refresh this page."
    )
    st.stop()

df = pd.read_csv(DATA_PATH)

RESIDUE_COLS = ["trash_tons", "tops_tons", "bagasse_tons", "press_mud_tons"]

# --- Summary metrics ---
total_farms = len(df)
harvest_ready = int((df["cane_tonnes"] > 0).sum())
total_cane = df["cane_tonnes"].sum()
total_residue = df["total_residue_tons"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total farms", total_farms)
col2.metric("Harvest-ready farms", f"{harvest_ready} / {total_farms}")
col3.metric("Total cane tonnage", f"{total_cane:,.0f} t")
col4.metric("Total residue tonnage", f"{total_residue:,.0f} t")

st.divider()

# --- Residue breakdown by type ---
st.subheader("Residue tonnage by type (all farms combined)")
type_totals = df[RESIDUE_COLS].sum().rename({
    "trash_tons": "Trash",
    "tops_tons": "Tops",
    "bagasse_tons": "Bagasse",
    "press_mud_tons": "Press mud",
})
st.bar_chart(type_totals)

st.divider()

# --- Top farms by residue ---
st.subheader("Top 15 farms by total residue")
top_farms = df.sort_values("total_residue_tons", ascending=False).head(15)
st.bar_chart(top_farms.set_index("farm_id")["total_residue_tons"])

st.divider()

# --- Full data table with filter ---
st.subheader("Farm-level data")
only_ready = st.checkbox("Show harvest-ready farms only", value=False)
display_df = df[df["cane_tonnes"] > 0] if only_ready else df
st.dataframe(display_df, use_container_width=True, hide_index=True)

st.download_button(
    "Download this view as CSV",
    display_df.to_csv(index=False).encode("utf-8"),
    file_name="residue_quantities_filtered.csv",
    mime="text/csv",
)

st.divider()

# --- Assumptions reference ---
with st.expander("Assumptions used in this calculation"):
    st.markdown("""
    | Residue type | RPR (t residue / t cane) |
    |---|---|
    | Trash | 0.10 |
    | Tops | 0.10 |
    | Bagasse | 0.30 |
    | Press mud | 0.03 |

    - Base yield: 30 tonnes/acre at full maturity
    - Harvest-ready threshold: 10 months
    - Full maturity: 12 months

    Full sources and reasoning are in RESIDUE_ASSUMPTIONS.md.
    """)
