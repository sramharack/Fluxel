
import json
import pandas as pd
from pathlib import Path

from flowforge_mep.water_flows import project_calculation

ROOT = Path(__file__).resolve().parents[1]


def test_ursuline_seed_replicates_workbook_totals():
    project = json.loads((ROOT / "data" / "ursuline_convent_seed_project.json").read_text(encoding="utf-8"))
    ashrae = pd.read_csv(ROOT / "data" / "ashrae_62_1_2022_table_6_1_user_provided.csv").to_dict("records")
    wastewater = pd.read_csv(ROOT / "data" / "wastewater_categories_corbitt.csv").to_dict("records")
    results = project_calculation(project, ashrae, wastewater)
    totals = results["totals"]

    assert round(totals["Daily Peak Occupancy"], 2) == 848.27
    assert round(totals["ADWF USgal/day"], 2) == 20099.05
    assert round(totals["ADWF m3/day"], 6) == round(76.08318071720515, 6)
    assert round(totals["Sewage Storage USgal"], 3) == round(30148.575, 3)
    assert round(totals["Potable Storage USgal"], 2) == 20099.05
    assert round(totals["Harmon Peak Factor"], 6) == round(3.8449411116281014, 6)


def test_building_2_and_9_match_workbook():
    project = json.loads((ROOT / "data" / "ursuline_convent_seed_project.json").read_text(encoding="utf-8"))
    ashrae = pd.read_csv(ROOT / "data" / "ashrae_62_1_2022_table_6_1_user_provided.csv").to_dict("records")
    wastewater = pd.read_csv(ROOT / "data" / "wastewater_categories_corbitt.csv").to_dict("records")
    results = project_calculation(project, ashrae, wastewater)
    by_id = {b["building_id"]: b for b in results["buildings"]}
    assert round(by_id["BLD 2"]["adwf_usgal_day"], 2) == 4715.00
    assert round(by_id["BLD 9"]["adwf_usgal_day"], 2) == 9785.00
