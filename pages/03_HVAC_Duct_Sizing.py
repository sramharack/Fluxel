import streamlit as st

from fluxel.hvac.duct_sizing import round_diameter_from_cfm_friction, round_diameter_from_cfm_velocity, velocity_from_cfm_diameter

st.set_page_config(page_title="Fluxel | Duct Sizing", page_icon="🌬️", layout="wide")
st.title("HVAC / Duct Sizing")
st.caption("Starter ductulator module for airflow, velocity, friction rate, and round duct equivalent.")

cfm = st.number_input("Airflow, CFM", min_value=0.0, value=1500.0)
velocity = st.number_input("Target velocity, FPM", min_value=0.0, value=950.0)
friction = st.number_input("Friction rate, in.wg / 100 ft", min_value=0.0, value=0.08, step=0.01)
diameter = st.number_input("Check round diameter, in", min_value=0.0, value=17.0)

c1, c2, c3 = st.columns(3)
c1.metric("Diameter from velocity", f"{round_diameter_from_cfm_velocity(cfm, velocity):.1f} in")
c2.metric("Diameter from friction", f"{round_diameter_from_cfm_friction(cfm, friction):.1f} in")
c3.metric("Velocity from diameter", f"{velocity_from_cfm_diameter(cfm, diameter):.0f} FPM")

st.info("Next step: add rectangular equivalent selector, friction graphs, and duct route pressure-loss schedules.")
