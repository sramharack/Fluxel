import pandas as pd

from fluxel.plumbing.water_flows import WaterFlowSettings, calculate_water_flows, harmon_peak_factor


def test_harmon_peak_factor_positive():
    assert harmon_peak_factor(1000) > 1


def test_water_flows_persons_override_area():
    rooms = pd.DataFrame([
        {
            "building": "A",
            "room_type": "Test",
            "area_ft2": 1000,
            "occupancy_category": "Office space",
            "qty": 2,
            "persons_per_room": 10,
            "wastewater_category": "Office / staff",
        }
    ])
    ashrae = pd.DataFrame([
        {"Occupancy Category": "Office space", "Default Occupant Density": 5}
    ])
    wastewater = pd.DataFrame([
        {"wastewater_category": "Office / staff", "per_capita_usgal_day": 15}
    ])
    result = calculate_water_flows(rooms, ashrae, wastewater, WaterFlowSettings())
    assert result["daily_peak_occupancy"] == 20
    assert result["adwf_usgal_day"] == 300
