from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="Fluxel | References", page_icon="📚", layout="wide")
st.title("Reference Tables")
st.caption("Editable project/reference data used by Fluxel modules.")

ashrae = pd.read_csv(ROOT / "data" / "plumbing" / "ashrae_62_1_2022_occupancy.csv")
wastewater = pd.read_csv(ROOT / "data" / "plumbing" / "wastewater_per_capita.csv")

st.subheader("ASHRAE 62.1-2022 occupancy density table")
st.dataframe(ashrae, use_container_width=True)

st.subheader("Wastewater per-capita design flow table")
st.dataframe(wastewater, use_container_width=True)

st.warning(
    "Keep copyrighted reference tables under proper office control. Do not publish tables publicly unless your office has permission to share them."
)
