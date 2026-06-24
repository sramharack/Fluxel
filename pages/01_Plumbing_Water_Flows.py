
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from fluxel.plumbing.water_flows import (
    project_calculation,
    comparison_to_workbook,
    make_flow_diagram_dot,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "plumbing"
ASHRAE_CSV = DATA_DIR / "ashrae_62_1_2022_table_6_1_user_provided.csv"
WASTEWATER_CSV = DATA_DIR / "wastewater_categories_corbitt.csv"
SEED_JSON = ROOT / "examples" / "convent_water_flows" / "demo_project.json"

st.set_page_config(page_title="Fluxel | Water Flows", page_icon="💧", layout="wide")


def load_refs():
    ashrae = pd.read_csv(ASHRAE_CSV)
    wastewater = pd.read_csv(WASTEWATER_CSV)
    return ashrae, wastewater


def load_seed_project():
    with open(SEED_JSON, "r", encoding="utf-8") as f:
        project = json.load(f)
    project.setdefault("metadata", {})
    project["metadata"].update({
        "project_mode": "demo_validation",
        "demo_name": "Convent Water Flows",
        "validation_source": "Convent - SR WFs.xlsx",
        "purpose": "Demo project used to validate Fluxel calculations against the spreadsheet."
    })
    return project


def new_blank_project():
    return {
        "project_name": "Untitled Water Flows Project",
        "project_location": "",
        "created_by": "",
        "reviewed_by": "",
        "code_basis": "Corbitt; ASHRAE 62.1-2022 Table 6-1; Barbados EPD retention basis; project-specific local requirements",
        "metadata": {
            "project_mode": "user_project",
            "purpose": "New user-created water flows project."
        },
        "settings": {
            "include_sewage_storage": True,
            "sewage_retention_days": 1.5,
            "include_potable_storage": True,
            "potable_storage_days": 1.0,
            "rainwater_flushing_percent": 0.0,
            "include_rainwater_branch": False,
            "harmon_factor_basis": "total_site_population",
            "potable_source_label": "B.W.A.",
            "water_filter_label": "Water filter",
            "water_filter_qty": 1,
            "potable_storage_qty": 1,
            "rainwater_source_label": "Rain water",
            "rainwater_suck_wells_label": "Rain water suck wells",
            "rainwater_suck_well_qty": 1,
            "septic_tanks_label": "Septic tanks",
            "septic_tank_qty": 1,
            "sewage_suck_wells_label": "Sewage suck wells",
            "sewage_suck_well_qty": 1
        },
        "buildings": []
    }


def convert_demo_to_user_project(project: dict) -> dict:
    copied = json.loads(json.dumps(project))
    copied.setdefault("metadata", {})
    copied["metadata"].update({
        "project_mode": "user_project",
        "purpose": "User project created from the Convent Water Flows demo template.",
        "copied_from_demo": "Convent Water Flows"
    })
    copied["project_name"] = f"New Project from {project.get('project_name', 'Demo')}"
    # Remove workbook validation totals so the copied project behaves like a normal project.
    for building in copied.get("buildings", []):
        building.pop("workbook_totals", None)
    return copied


def ensure_project():
    # Default to the demo so the app immediately shows useful validated behaviour.
    # The sidebar provides a one-click New Blank Project action for real projects.
    if "project" not in st.session_state:
        st.session_state.project = load_seed_project()
    if "last_results" not in st.session_state:
        st.session_state.last_results = None


def json_download(project: dict) -> bytes:
    return json.dumps(project, indent=2, ensure_ascii=False).encode("utf-8")


def format_number_columns(df: pd.DataFrame, digits=2) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].astype(float).round(digits)
    return out


ensure_project()
dash_style = """
<style>
[data-testid="stMetricValue"] {font-size: 1.45rem;}
.small-note {font-size: 0.86rem; color: #64748b;}
.block-title {font-size: 1.0rem; font-weight: 700; color: #0f172a; margin-top: 0.4rem;}
</style>
"""
st.markdown(dash_style, unsafe_allow_html=True)

ashrae_df, wastewater_df = load_refs()
ashrae_records = ashrae_df.to_dict("records")
wastewater_records = wastewater_df.to_dict("records")
ashrae_categories = ashrae_df["occupancy_category"].dropna().tolist()
waste_categories = wastewater_df["category"].dropna().tolist()

st.title("Fluxel — Plumbing Water Flows")
st.caption("First module: average dry-weather wastewater flow, septic/storage separation, potable storage, Harmon peak factor, and site flow diagram.")

with st.sidebar:
    st.header("Project")
    current_mode = st.session_state.project.get("metadata", {}).get("project_mode", "user_project")
    if current_mode == "demo_validation":
        st.success("Demo validation project loaded")
        st.caption("Use this to prove the app matches the Convent spreadsheet, then create or import a new project.")
    else:
        st.info("User project mode")

    c_demo, c_new = st.columns(2)
    with c_demo:
        if st.button("Load demo", use_container_width=True):
            st.session_state.project = load_seed_project()
            st.session_state.last_results = None
            st.rerun()
    with c_new:
        if st.button("New blank", use_container_width=True):
            st.session_state.project = new_blank_project()
            st.session_state.last_results = None
            st.rerun()

    if current_mode == "demo_validation":
        if st.button("Copy demo as new project", use_container_width=True):
            st.session_state.project = convert_demo_to_user_project(st.session_state.project)
            st.session_state.last_results = None
            st.rerun()

    uploaded = st.file_uploader("Import project JSON", type=["json"])
    if uploaded is not None:
        try:
            st.session_state.project = json.loads(uploaded.read().decode("utf-8"))
            st.session_state.last_results = None
            st.success("Project imported.")
        except Exception as exc:
            st.error(f"Could not import JSON: {exc}")

    st.download_button(
        "Export project JSON",
        data=json_download(st.session_state.project),
        file_name="fluxel_water_flows_project.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()
    st.markdown("**Calculation control**")
    st.caption("Changes are saved in the app state. Press Calculate when you want updated results.")
    calculate_now = st.button("Calculate water flows", type="primary", use_container_width=True)
    st.caption("Export JSON before closing the browser if you want to keep the project file.")

project = st.session_state.project

tabs = st.tabs(["1 Project setup", "2 References", "3 Buildings + rooms", "4 Results", "5 Flow diagram", "6 Workbook check"])

with tabs[0]:
    st.subheader("Project setup")
    mode = project.get("metadata", {}).get("project_mode", "user_project")
    if mode == "demo_validation":
        st.info("This is the Convent Water Flows demo/validation project. Use **Workbook check** to confirm the Python app matches the spreadsheet. Use **New blank** or **Copy demo as new project** for actual projects.")
    else:
        st.success("This is a normal user project. The workbook validation tab will only show data when validation totals are present.")
    col1, col2 = st.columns(2)
    with col1:
        project["project_name"] = st.text_input("Project name", project.get("project_name", ""))
        project["project_location"] = st.text_input("Project location", project.get("project_location", ""))
        project["created_by"] = st.text_input("Created by", project.get("created_by", ""))
    with col2:
        project["reviewed_by"] = st.text_input("Reviewed by", project.get("reviewed_by", ""))
        project["code_basis"] = st.text_input("Code / reference basis", project.get("code_basis", ""))

    st.subheader("Storage and peak-flow settings")
    settings = project.setdefault("settings", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        settings["include_sewage_storage"] = st.checkbox("Include sewage/septic storage", value=bool(settings.get("include_sewage_storage", True)))
        settings["sewage_retention_days"] = st.number_input("Sewage retention days", min_value=0.0, value=float(settings.get("sewage_retention_days", 1.5)), step=0.5, disabled=not settings["include_sewage_storage"])
    with c2:
        settings["include_potable_storage"] = st.checkbox("Include potable water storage", value=bool(settings.get("include_potable_storage", True)))
        settings["potable_storage_days"] = st.number_input("Potable storage days", min_value=0.0, value=float(settings.get("potable_storage_days", 1.0)), step=0.5, disabled=not settings["include_potable_storage"])
    with c3:
        settings["rainwater_flushing_percent"] = st.number_input("Optional rainwater flushing allowance, %", min_value=0.0, max_value=100.0, value=float(settings.get("rainwater_flushing_percent", 30.0)), step=5.0)
    with c4:
        settings["harmon_factor_basis"] = st.selectbox("Harmon factor basis", ["total_site_population"], index=0)
        st.caption("Matches the workbook: all building populations are summed first.")

    st.info("Sewage/septic storage and potable storage are now separate settings. You can switch sewage storage off for projects where only average/peak flows are required.")

    with st.expander("Flow diagram equipment labels and quantities", expanded=False):
        st.caption("These fields only control the professional site flow chart labels. They do not change the engineering calculation unless noted.")
        f1, f2, f3 = st.columns(3)
        with f1:
            settings["potable_source_label"] = st.text_input("Potable source label", settings.get("potable_source_label", "B.W.A."))
            settings["water_filter_label"] = st.text_input("Treatment/filter label", settings.get("water_filter_label", "Water filter"))
            settings["water_filter_qty"] = st.number_input("Water filter qty", min_value=0, value=int(settings.get("water_filter_qty", 1)), step=1)
            settings["potable_storage_qty"] = st.number_input("Potable storage tank qty", min_value=0, value=int(settings.get("potable_storage_qty", 1)), step=1)
        with f2:
            settings["include_rainwater_branch"] = st.checkbox("Show rainwater/flushing branch", value=bool(settings.get("include_rainwater_branch", settings.get("rainwater_flushing_percent", 0) > 0)))
            settings["rainwater_source_label"] = st.text_input("Rainwater source label", settings.get("rainwater_source_label", "Rain water"))
            settings["rainwater_suck_wells_label"] = st.text_input("Rainwater collection label", settings.get("rainwater_suck_wells_label", "Rain water suck wells"))
            settings["rainwater_suck_well_qty"] = st.number_input("Rainwater suck well qty", min_value=0, value=int(settings.get("rainwater_suck_well_qty", 1)), step=1)
        with f3:
            settings["septic_tanks_label"] = st.text_input("Septic storage label", settings.get("septic_tanks_label", "Septic tanks"))
            settings["septic_tank_qty"] = st.number_input("Septic tank qty", min_value=0, value=int(settings.get("septic_tank_qty", 1)), step=1)
            settings["sewage_suck_wells_label"] = st.text_input("Sewage disposal label", settings.get("sewage_suck_wells_label", "Sewage suck wells"))
            settings["sewage_suck_well_qty"] = st.number_input("Sewage suck well qty", min_value=0, value=int(settings.get("sewage_suck_well_qty", 1)), step=1)

with tabs[1]:
    st.subheader("Reference tables")
    st.markdown("These are the tables the calculator uses for lookups.")

    with st.expander("ASHRAE 62.1-2022 Table 6-1 values — user provided", expanded=True):
        st.dataframe(ashrae_df, use_container_width=True, height=420)
        st.download_button("Download ASHRAE reference CSV", ashrae_df.to_csv(index=False).encode("utf-8"), "ashrae_62_1_2022_table_6_1.csv", "text/csv")
        st.caption("Occupancy density is stored as #/1000 ft². The calculator converts this to capita/ft² by dividing by 1000.")

    with st.expander("Corbitt / workbook wastewater design categories", expanded=True):
        st.dataframe(wastewater_df, use_container_width=True, height=320)
        st.download_button("Download wastewater reference CSV", wastewater_df.to_csv(index=False).encode("utf-8"), "wastewater_categories_corbitt.csv", "text/csv")
        st.caption("These values were extracted from the Convent Water Flows sheet. The litres/day values are calculated from US gallons using 1 USgal = 3.785411784 L.")

    st.markdown("""
**Implemented formulas**

- Area-based occupancy = room area × quantity × ASHRAE occupant density.
- Persons-based occupancy = persons per room × quantity.
- Average daily wastewater flow = daily peak occupancy × per-capita wastewater flow.
- Septic tank storage = ADWF × selected sewage retention days, if enabled.
- Potable storage = daily potable demand × selected potable storage days, if enabled.
- Harmon peak factor = `1 + 14 / (4 + sqrt(P / 1000))`, matching the workbook behaviour.
""")

with tabs[2]:
    st.subheader("Create and edit building objects")
    buildings = project.setdefault("buildings", [])

    bld_df = pd.DataFrame([
        {"building_id": b.get("building_id", ""), "description": b.get("description", ""), "room_count": len(b.get("rooms", []))}
        for b in buildings
    ])
    edited_bld = st.data_editor(
        bld_df,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "building_id": st.column_config.TextColumn("Building ID", required=True),
            "description": st.column_config.TextColumn("Description"),
            "room_count": st.column_config.NumberColumn("Rooms", disabled=True),
        },
        key="building_editor",
    )
    if st.button("Apply building list changes"):
        old = {b.get("building_id", ""): b for b in buildings}
        new_buildings = []
        for row in edited_bld.to_dict("records"):
            bid = str(row.get("building_id") or "").strip()
            if not bid:
                continue
            existing = old.get(bid, {"rooms": []})
            existing["building_id"] = bid
            existing["description"] = str(row.get("description") or "")
            new_buildings.append(existing)
        project["buildings"] = new_buildings
        st.success("Building list updated.")
        st.rerun()

    if not project.get("buildings"):
        st.warning("Create at least one building.")
    else:
        st.divider()
        st.subheader("Room rows")
        bld_ids = [b["building_id"] for b in project["buildings"]]
        selected_bid = st.selectbox("Select building", bld_ids)
        selected_index = bld_ids.index(selected_bid)
        building = project["buildings"][selected_index]
        st.caption(building.get("description", ""))

        default_room = {
            "room_type": "New room",
            "input_method": "Persons",
            "area_ft2": None,
            "persons_per_room": 1.0,
            "quantity": 1.0,
            "ashrae_occupancy_category": "Office space",
            "wastewater_category": "Staff",
            "manual_density_capita_per_ft2": None,
            "manual_per_capita_usgal_day": None,
            "notes": "",
        }
        if "rooms" not in building or not building["rooms"]:
            building["rooms"] = [default_room.copy()]

        editable_cols = [
            "room_type", "input_method", "area_ft2", "persons_per_room", "quantity",
            "ashrae_occupancy_category", "wastewater_category",
            "manual_density_capita_per_ft2", "manual_per_capita_usgal_day", "notes"
        ]
        room_df = pd.DataFrame(building.get("rooms", []))
        for col in editable_cols:
            if col not in room_df.columns:
                room_df[col] = None
        room_df = room_df[editable_cols]

        edited_rooms = st.data_editor(
            room_df,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            height=520,
            column_config={
                "room_type": st.column_config.TextColumn("Room type", required=True),
                "input_method": st.column_config.SelectboxColumn("Input method", options=["Persons", "Area"], required=True),
                "area_ft2": st.column_config.NumberColumn("Area ft²", min_value=0.0, help="Used only when input method is Area."),
                "persons_per_room": st.column_config.NumberColumn("Persons / room", min_value=0.0, help="Used only when input method is Persons."),
                "quantity": st.column_config.NumberColumn("Qty", min_value=0.0, required=True),
                "ashrae_occupancy_category": st.column_config.SelectboxColumn("ASHRAE occupancy category", options=ashrae_categories),
                "wastewater_category": st.column_config.SelectboxColumn("Wastewater category", options=[""] + waste_categories),
                "manual_density_capita_per_ft2": st.column_config.NumberColumn("Manual density capita/ft²", min_value=0.0, help="Optional override for area method."),
                "manual_per_capita_usgal_day": st.column_config.NumberColumn("Manual wastewater USgal/cap/day", min_value=0.0, help="Optional override for wastewater category."),
                "notes": st.column_config.TextColumn("Notes"),
            },
            key=f"rooms_editor_{selected_bid}",
        )
        project["buildings"][selected_index]["rooms"] = edited_rooms.where(pd.notna(edited_rooms), None).to_dict("records")
        st.caption("For each row, select either Persons or Area. The calculator ignores the non-selected input field and reports a warning when both are filled.")

if calculate_now:
    st.session_state.last_results = project_calculation(project, ashrae_records, wastewater_records)
    if st.session_state.last_results.get("errors"):
        st.warning("Calculated with input errors. Review the messages in Results.")
    else:
        st.success("Calculation complete.")

results = st.session_state.last_results

with tabs[3]:
    st.subheader("Results")
    if results is None:
        st.info("Press **Calculate water flows** in the sidebar to generate results.")
    else:
        totals = results["totals"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Daily peak occupancy", f"{totals['Daily Peak Occupancy']:,.2f}")
        m2.metric("ADWF", f"{totals['ADWF USgal/day']:,.0f} USgal/day")
        m3.metric("Harmon peak factor", f"{totals['Harmon Peak Factor']:.3f}")
        m4.metric("Hourly peak SWF", f"{totals['Hourly Peak SWF USgal/hr']:,.0f} USgal/hr")

        s1, s2 = st.columns(2)
        with s1:
            st.markdown("<div class='block-title'>Sewage / septic storage</div>", unsafe_allow_html=True)
            if results["settings"].get("include_sewage_storage", True):
                st.metric("Storage required", f"{totals['Sewage Storage USgal']:,.0f} USgal", f"{results['settings'].get('sewage_retention_days')} day(s)")
            else:
                st.info("Sewage/septic storage disabled for this project.")
        with s2:
            st.markdown("<div class='block-title'>Potable water storage</div>", unsafe_allow_html=True)
            if results["settings"].get("include_potable_storage", True):
                st.metric("Storage required", f"{totals['Potable Storage USgal']:,.0f} USgal", f"{results['settings'].get('potable_storage_days')} day(s)")
            else:
                st.info("Potable storage disabled for this project.")

        if results.get("errors"):
            with st.expander("Input errors", expanded=True):
                for e in results["errors"]:
                    st.error(e)
        if results.get("warnings"):
            with st.expander("Input warnings", expanded=False):
                for w in results["warnings"][:200]:
                    st.warning(w)

        summary_df = pd.DataFrame(results["summary_rows"])
        st.markdown("### Building summary")
        st.dataframe(format_number_columns(summary_df, 2), use_container_width=True, height=520)
        st.download_button("Download building summary CSV", summary_df.to_csv(index=False).encode("utf-8"), "water_flow_building_summary.csv", "text/csv")

        chart_df = summary_df[["Location", "ADWF USgal/day", "Potable Storage USgal", "Sewage Storage USgal"]].copy()
        fig = px.bar(chart_df, x="Location", y="ADWF USgal/day", title="Average Daily Wastewater Flow by Building")
        fig.update_layout(xaxis_title="Building", yaxis_title="USgal/day", height=420)
        st.plotly_chart(fig, use_container_width=True)

with tabs[4]:
    st.subheader("Site flow diagram — provisional")
    if results is None:
        st.info("Press **Calculate water flows** in the sidebar to generate the flow diagram.")
    else:
        st.graphviz_chart(make_flow_diagram_dot(results), use_container_width=True)
        st.caption("Diagram output is provisional. Quantities update after pressing Calculate Water Flows. We will refine the professional arrow layout later.")

with tabs[5]:
    st.subheader("Workbook replication check")
    mode = project.get("metadata", {}).get("project_mode", "user_project")
    if mode == "demo_validation":
        st.caption("Demo source: Convent - SR WFs.xlsx / Convent Water Flows sheet")
    else:
        st.caption("This tab is normally blank for user-created projects unless workbook validation totals are imported with the project JSON.")

    if results is None:
        st.info("Press **Calculate water flows** in the sidebar to compare the demo data against the attached workbook totals.")
    else:
        comp = pd.DataFrame(comparison_to_workbook(results))
        if comp.empty:
            st.info("No workbook totals stored in the current project JSON. This is expected for normal user projects.")
        else:
            st.dataframe(format_number_columns(comp, 6), use_container_width=True, height=520)
            total_abs_delta = comp["Δ ADWF USgal/day"].abs().sum()
            if total_abs_delta < 0.001:
                st.success("Demo calculation matches the extracted workbook building ADWF totals.")
            else:
                st.warning(f"Total absolute ADWF delta: {total_abs_delta:,.3f} USgal/day. Review rows with non-zero delta.")
