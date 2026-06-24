import pandas as pd
import streamlit as st

from fluxel.electrical.load_calcs import demand_kw, kva_from_kw, three_phase_current

st.set_page_config(page_title="Fluxel | Electrical Loads", page_icon="⚡", layout="wide")
st.title("Electrical / Load Calculator")
st.caption("Starter module for connected load, demand load, kVA, and current.")

connected_kw = st.number_input("Connected load, kW", min_value=0.0, value=100.0)
demand_factor = st.number_input("Demand factor", min_value=0.0, max_value=1.5, value=1.0, step=0.05)
spare_percent = st.number_input("Spare/growth allowance, %", min_value=0.0, value=20.0, step=5.0)
pf = st.number_input("Power factor", min_value=0.1, max_value=1.0, value=0.9, step=0.01)
voltage = st.number_input("3-phase voltage, V L-L", min_value=1.0, value=400.0)

kw = demand_kw(connected_kw, demand_factor, spare_percent)
kva = kva_from_kw(kw, pf)
amps = three_phase_current(kva, voltage)

c1, c2, c3 = st.columns(3)
c1.metric("Demand load", f"{kw:,.1f} kW")
c2.metric("Apparent load", f"{kva:,.1f} kVA")
c3.metric("Current", f"{amps:,.1f} A")

st.info("This is a starter module. Add NEC/IEC demand categories, panel schedules, and cable sizing later.")
