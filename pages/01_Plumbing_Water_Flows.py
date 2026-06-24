from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from fluxel.common.diagrams import make_site_flow_svg
from fluxel.plumbing.water_flows import WaterFlowSettings, calculate_water_flows, starter_rooms
from fluxel.reports.export import dataframe_to_csv_bytes, dict_to_json_bytes

ROOT = Path(__file__).resolve().parents[1]
ASHRAE_PATH = ROOT / "data" / "plumbing" / "ashrae_62_1_2022_occupancy.csv"
WW_PATH = ROOT / "data" / "plumbing" / "wastewater_per_capita.csv"
DEMO_PATH = ROOT / "examples" / "convent_water_flows" / "demo_project.json"

st.set_page_config(page_title="Fluxel | Water Flows", page_icon="💧", layout="wide")
st.title("Plumbing / Water Flows")
st.caption("Building-room based wastewater, potable storage, sewage storage, Harmon peak flow, and site flow diagram.")

@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)

ashrae = load_csv(ASHRAE_PATH)
wastewater = load_csv(WW_PATH)

if "water_rooms" not in st.session_state:
    st.session_state.water_rooms = starter_rooms()
if "water_results" not in st.session_state:
    st.session_state.water_results = None
if "project_name" not in st.session_state:
    st.session_state.project_name = "New Fluxel Project"

with st.sidebar:
    st.header("Project")
    st.session_state.project_name = st.text_input("Project name", st.session_state.project_name)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("New blank", use_container_width=True):
            st.session_state.water_rooms = pd.DataFrame(
                columns=["building", "room_type", "area_ft2", "occupancy_category", "qty", "persons_per_room", "wastewater_category"]
            )
            st.session_state.water_results = None
            st.session_state.project_name = "New Fluxel Project"
            st.rerun()
    with col_b:
        if st.button("Load demo", use_container_width=True):
            demo = json.loads(DEMO_PATH.read_text())
            st.session_state.project_name = demo["project_name"]
            st.session_state.water_rooms = pd.DataFrame(demo["rooms"])
            st.session_state.water_results = None
            st.rerun()

    st.divider()
    st.header("Storage settings")
    sewage_enabled = st.checkbox("Include sewage/septic storage", value=True)
    potable_enabled = st.checkbox("Include potable storage", value=True)
    sewage_days = st.number_input("Sewage retention, days", min_value=0.0, value=1.5, step=0.5)
    potable_days = st.number_input("Potable storage, days", min_value=0.0, value=1.0, step=0.5)
    flushing_percent = st.number_input("Flushing reuse allowance, %", min_value=0.0, max_value=100.0, value=30.0, step=5.0)

    st.divider()
    st.header("Diagram equipment")
    water_filter_qty = st.number_input("Water filter qty", min_value=0, value=1, step=1)
    rainwater_well_qty = st.number_input("Rainwater suck well qty", min_value=0, value=1, step=1)
    septic_tank_qty = st.number_input("Septic tank qty", min_value=0, value=1, step=1)
    sewage_well_qty = st.number_input("Sewage suck well qty", min_value=0, value=1, step=1)

settings = WaterFlowSettings(
    sewage_storage_enabled=sewage_enabled,
    potable_storage_enabled=potable_enabled,
    sewage_retention_days=sewage_days,
    potable_storage_days=potable_days,
    flushing_percent=flushing_percent,
)

tab_input, tab_results, tab_diagram, tab_export = st.tabs(["Input", "Results", "Site flow diagram", "Export"])

with tab_input:
    st.subheader("Building room schedule")
    st.write("Use either area or persons per room. If both are entered, persons are used and the row is flagged.")

    edited = st.data_editor(
        st.session_state.water_rooms,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "occupancy_category": st.column_config.SelectboxColumn(
                "occupancy_category",
                options=ashrae["Occupancy Category"].dropna().tolist(),
            ),
            "wastewater_category": st.column_config.SelectboxColumn(
                "wastewater_category",
                options=wastewater["wastewater_category"].dropna().tolist(),
            ),
        },
    )
    st.session_state.water_rooms = edited

    if st.button("Calculate Water Flows", type="primary"):
        results = calculate_water_flows(edited, ashrae, wastewater, settings)
        results["project_name"] = st.session_state.project_name
        st.session_state.water_results = results
        st.success("Water flow results updated.")

with tab_results:
    if st.session_state.water_results is None:
        st.info("Press **Calculate Water Flows** on the Input tab to update results.")
    else:
        r = st.session_state.water_results
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Daily peak occupancy", f"{r['daily_peak_occupancy']:,.1f}")
        c2.metric("ADWF", f"{r['adwf_usgal_day']:,.0f} USgal/day")
        c3.metric("ADWF", f"{r['adwf_m3_day']:,.1f} m³/day")
        c4.metric("Harmon PF", f"{r['harmon_peak_factor']:.3f}")

        c5, c6, c7 = st.columns(3)
        c5.metric("Potable storage", f"{r['potable_storage_usgal']:,.0f} USgal")
        c6.metric("Sewage storage", f"{r['sewage_storage_usgal']:,.0f} USgal")
        c7.metric("Peak SWF", f"{r['peak_swf_usgal_hr']:,.0f} USgal/hr")

        st.subheader("Building summary")
        st.dataframe(r["building_summary"], use_container_width=True)

        warnings = r["room_calcs"][r["room_calcs"]["input_warning"] != ""]
        if not warnings.empty:
            st.warning("Some rows have both area and persons entered. Persons were used for those rows.")
            st.dataframe(warnings[["building", "room_type", "input_warning"]], use_container_width=True)

with tab_diagram:
    if st.session_state.water_results is None:
        st.info("Press **Calculate Water Flows** on the Input tab to update the diagram.")
    else:
        equipment = {
            "water_filter_qty": water_filter_qty,
            "rainwater_well_qty": rainwater_well_qty,
            "septic_tank_qty": septic_tank_qty,
            "sewage_well_qty": sewage_well_qty,
        }
        svg = make_site_flow_svg(st.session_state.water_results, equipment)
        components.html(svg, height=650, scrolling=True)

with tab_export:
    st.subheader("Project export")
    project_payload = {
        "project_name": st.session_state.project_name,
        "rooms": st.session_state.water_rooms.to_dict(orient="records"),
        "settings": settings.__dict__,
    }
    st.download_button(
        "Download project JSON",
        data=dict_to_json_bytes(project_payload),
        file_name="fluxel_water_flows_project.json",
        mime="application/json",
    )

    if st.session_state.water_results is not None:
        st.download_button(
            "Download building summary CSV",
            data=dataframe_to_csv_bytes(st.session_state.water_results["building_summary"]),
            file_name="water_flows_building_summary.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download room calculations CSV",
            data=dataframe_to_csv_bytes(st.session_state.water_results["room_calcs"]),
            file_name="water_flows_room_calculations.csv",
            mime="text/csv",
        )
