import json
from pathlib import Path

import pandas as pd

from fluxel.plumbing.water_flows import (
    harmon_peak_factor,
    project_calculation,
    comparison_to_workbook,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "plumbing"
DEMO = ROOT / "examples" / "convent_water_flows" / "demo_project.json"


def _load_demo_inputs():
    project = json.loads(DEMO.read_text(encoding="utf-8"))
    ashrae = pd.read_csv(DATA / "ashrae_62_1_2022_table_6_1_user_provided.csv").to_dict("records")
    wastewater = pd.read_csv(DATA / "wastewater_categories_corbitt.csv").to_dict("records")
    return project, ashrae, wastewater


def test_harmon_peak_factor_positive():
    assert harmon_peak_factor(1000) > 1


def test_convent_demo_replicates_workbook_totals():
    project, ashrae, wastewater = _load_demo_inputs()
    results = project_calculation(project, ashrae, wastewater)
    totals = results["totals"]

    assert round(totals["Daily Peak Occupancy"], 2) == 848.27
    assert round(totals["ADWF USgal/day"], 2) == 20099.05
    assert round(totals["ADWF m3/day"], 6) == round(76.08318071720515, 6)
    assert round(totals["Sewage Storage USgal"], 3) == round(30148.575, 3)
    assert round(totals["Potable Storage USgal"], 2) == 20099.05
    assert round(totals["Harmon Peak Factor"], 6) == round(3.8449411116281014, 6)


def test_demo_workbook_comparison_rows_are_available():
    project, ashrae, wastewater = _load_demo_inputs()
    results = project_calculation(project, ashrae, wastewater)
    comp = comparison_to_workbook(results)
    assert len(comp) > 0
    assert sum(abs(row["Δ ADWF USgal/day"]) for row in comp) < 0.001


def test_user_project_area_and_person_methods_work():
    project = {
        "project_name": "Unit test project",
        "settings": {
            "include_sewage_storage": True,
            "sewage_retention_days": 1.5,
            "include_potable_storage": True,
            "potable_storage_days": 1.0,
            "rainwater_flushing_percent": 0.0,
        },
        "buildings": [
            {
                "building_id": "A",
                "description": "Sample building",
                "rooms": [
                    {
                        "room_type": "Office area",
                        "input_method": "Area",
                        "area_ft2": 1000,
                        "persons_per_room": None,
                        "quantity": 1,
                        "ashrae_occupancy_category": "Office space",
                        "wastewater_category": "Staff",
                    },
                    {
                        "room_type": "Manual persons",
                        "input_method": "Persons",
                        "area_ft2": None,
                        "persons_per_room": 10,
                        "quantity": 2,
                        "ashrae_occupancy_category": "Office space",
                        "wastewater_category": "Staff",
                    },
                ],
            }
        ],
    }
    _, ashrae, wastewater = _load_demo_inputs()
    results = project_calculation(project, ashrae, wastewater)
    totals = results["totals"]
    # Office density 5 / 1000 ft² gives 5 people from the area row, plus 20 from manual persons.
    assert totals["Daily Peak Occupancy"] == 25
    assert totals["ADWF USgal/day"] == 25 * 15
