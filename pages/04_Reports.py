import streamlit as st

st.set_page_config(page_title="Fluxel | Reports", page_icon="📄", layout="wide")
st.title("Reports")
st.caption("Starter area for calculation report exports.")

st.markdown(
    """
Planned report outputs:

- Project cover sheet
- Design criteria and assumptions
- Calculation tables
- Building summaries
- Site flow diagram
- Reviewer/signoff block
- Excel export
- PDF export
"""
)
