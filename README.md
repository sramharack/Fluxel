# FlowForge MEP — Water Flows Module

This is a Streamlit prototype for the first FlowForge MEP module: site water-flow and storage estimation.

The included **Convent Water Flows** dataset is treated as a **demo / validation project**, not as the only working project. It is loaded by default so a new user immediately sees a complete working example and can check the Python calculation results against the original spreadsheet behaviour.

## Project modes

The app supports two practical modes:

1. **Demo validation project**
   - Loads the Convent Water Flows example.
   - Includes workbook validation totals.
   - Enables the Workbook Check tab to prove the app matches the spreadsheet.

2. **User project mode**
   - Start from **New blank** in the sidebar.
   - Or use **Copy demo as new project** to reuse the demo structure without workbook validation totals.
   - Export/import project JSON files for saving and sharing.

## Included features

- Building objects and room-by-room input rows
- Persons-based or area-based occupancy input
- ASHRAE 62.1-2022 Table 6-1 occupancy density lookup
- Corbitt/workbook wastewater category lookup
- Average dry-weather wastewater flow calculation
- Optional sewage/septic storage calculation
- Separate potable-water demand and storage calculation
- Harmon peak factor and hourly peak sanitary wastewater flow
- Clean engineering-style block flow diagram
- Workbook replication check against the extracted seed totals
- JSON project export/import

## Fast browser-only prototype route

Use GitHub Codespaces or Replit so you do not have to install Python locally.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Recommended demo flow

1. Launch the app.
2. Press **Calculate water flows**.
3. Go to **Workbook check** to confirm the Convent demo matches the spreadsheet.
4. Go to **Results** and **Flow diagram** to show the utility of the app.
5. Press **New blank** to create a fresh project, or **Copy demo as new project** to use the demo as a starting template.
6. Export the project JSON when done.

## Core calculation behaviour

### Room occupancy

For each room row, choose one input method:

- **Persons**: `daily peak occupancy = persons per room × quantity`
- **Area**: `daily peak occupancy = area ft² × quantity × ASHRAE occupant density`

ASHRAE density is stored as `#/1000 ft²`, so the app converts it to `capita/ft²` by dividing by 1000.

### Wastewater flow

```text
ADWF = daily peak occupancy × per-capita wastewater flow
```

### Sewage / septic storage

```text
Septic storage = ADWF × sewage retention days
```

This is optional and separate from potable-water storage.

### Potable-water storage

```text
Potable storage = potable daily demand × potable storage days
```

The seed project matches the workbook approach where daily potable demand is taken from the average daily water/wastewater demand total.

### Harmon peak factor

The current implementation intentionally matches the workbook:

```text
Harmon PF = 1 + 14 / (4 + sqrt(P / 1000))
```

Where `P` is the total site population.

## Data included

- `data/ursuline_convent_seed_project.json` — extracted project seed data from the Convent Water Flows sheet.
- `data/wastewater_categories_corbitt.csv` — wastewater category values extracted from the workbook.
- `data/ashrae_62_1_2022_table_6_1_user_provided.csv` — user-provided ASHRAE table values.

## Notes for professional use

This is a prototype. Before using on signed engineering work, verify all formulas, reference tables, code basis, local authority requirements, and project assumptions.
