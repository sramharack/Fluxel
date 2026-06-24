# Fluxel

**Fluxel** is a Streamlit-based MEP design calculation suite for fast engineering prototypes, validation against office spreadsheets, and clean report outputs.

The first production module is **Plumbing → Water Flows**, based around site/building water and wastewater demand, septic retention, potable storage, and site flow diagrams. The repo is structured to expand into electrical, HVAC, fire alarm, hydronics, and report generation.

## GitHub repo description

> Fluxel — an open MEP design calculation suite for plumbing, HVAC, electrical, fire alarm, and engineering report workflows.

## Current modules

- **Plumbing / Public Health**
  - Water flow calculator
  - Building and room object input
  - ASHRAE occupancy-density lookup table
  - Per-capita wastewater flow lookup
  - Average dry weather flow calculation
  - Septic/sewage storage allowance
  - Potable water storage allowance
  - Site flow diagram output

- **Electrical**
  - Starter load calculator
  - kW, kVA, current, and spare capacity basis

- **HVAC / Mechanical**
  - Starter duct sizing calculator
  - CFM, friction rate, velocity, and round duct equivalent

- **Reports**
  - Starter export helpers for CSV/JSON
  - Future Excel/PDF calculation packs

## Quick start: GitHub Codespaces

1. Create a GitHub repo named `fluxel-mep`.
2. Upload these files.
3. Open the repo in GitHub Codespaces.
4. Run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```text
fluxel-mep/
├─ app.py
├─ pages/
│  ├─ 01_Plumbing_Water_Flows.py
│  ├─ 02_Electrical_Loads.py
│  ├─ 03_HVAC_Duct_Sizing.py
│  ├─ 04_Reports.py
│  └─ 99_References.py
│
├─ fluxel/
│  ├─ common/
│  │  ├─ diagrams.py
│  │  ├─ project.py
│  │  └─ units.py
│  ├─ plumbing/
│  │  └─ water_flows.py
│  ├─ electrical/
│  │  └─ load_calcs.py
│  ├─ hvac/
│  │  └─ duct_sizing.py
│  └─ reports/
│     └─ export.py
│
├─ data/
│  ├─ plumbing/
│  │  ├─ ashrae_62_1_2022_occupancy.csv
│  │  └─ wastewater_per_capita.csv
│  ├─ electrical/
│  └─ hvac/
│
├─ examples/
│  └─ convent_water_flows/
│     └─ demo_project.json
│
├─ docs/
├─ tests/
└─ requirements.txt
```

## Development rule

Keep engineering calculations out of Streamlit pages. Streamlit is only the interface. Calculation logic belongs in the `fluxel/` package so it can be tested and reused.

## Validation approach

The Convent Water Flows project should remain an example validation project. Users should be able to load it as a demo, compare outputs against the original spreadsheet, and then create new projects without modifying the validation baseline.

## Engineering disclaimer

Fluxel is a calculation aid. Final engineering decisions must be reviewed and signed off by a qualified engineer using the applicable code, authority requirements, and project-specific assumptions.
