import streamlit as st

st.set_page_config(
    page_title="Fluxel",
    page_icon="⚙️",
    layout="wide",
)

st.title("Fluxel")
st.subheader("MEP design calculation suite")

st.markdown(
    """
Fluxel is being built as a full MEP design suite: plumbing/public-health, HVAC, electrical, fire alarm, hydronics, and report workflows.

The first working module is **Plumbing → Water Flows**. Use the sidebar pages to open modules.
"""
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("First module", "Water Flows")
    st.caption("Building/room based wastewater and potable demand.")

with col2:
    st.metric("Design target", "MEP suite")
    st.caption("One repo, separate engineering modules.")

with col3:
    st.metric("Workflow", "Demo + New Projects")
    st.caption("Validate against example spreadsheets, then create clean projects.")

st.info(
    "Development rule: keep calculations in the `fluxel/` package and keep Streamlit pages as the user interface only."
)
