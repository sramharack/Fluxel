from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt
from typing import Any

import pandas as pd

from fluxel.common.units import USGAL_PER_M3


@dataclass
class WaterFlowSettings:
    sewage_storage_enabled: bool = True
    potable_storage_enabled: bool = True
    sewage_retention_days: float = 1.5
    potable_storage_days: float = 1.0
    flushing_percent: float = 30.0
    use_harmon_site_population: bool = True


REQUIRED_ROOM_COLUMNS = [
    "building",
    "room_type",
    "area_ft2",
    "occupancy_category",
    "qty",
    "persons_per_room",
    "wastewater_category",
]


def harmon_peak_factor(population: float) -> float:
    """Harmon peaking factor using population in persons.

    P is population in thousands.
    """
    if population <= 0:
        return 0.0
    p_thousand = population / 1000.0
    return 1.0 + (14.0 / (4.0 + sqrt(p_thousand)))


def normalize_room_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in REQUIRED_ROOM_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col in ["building", "room_type", "occupancy_category", "wastewater_category"] else 0.0
    numeric_cols = ["area_ft2", "qty", "persons_per_room"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["qty"] = df["qty"].replace(0, 1)
    return df[REQUIRED_ROOM_COLUMNS]


def calculate_water_flows(
    rooms: pd.DataFrame,
    ashrae: pd.DataFrame,
    wastewater: pd.DataFrame,
    settings: WaterFlowSettings | None = None,
) -> dict[str, Any]:
    settings = settings or WaterFlowSettings()
    rooms = normalize_room_table(rooms)

    ash = ashrae[["Occupancy Category", "Default Occupant Density"]].copy()
    ash["Default Occupant Density"] = pd.to_numeric(ash["Default Occupant Density"], errors="coerce").fillna(0.0)

    ww = wastewater[["wastewater_category", "per_capita_usgal_day"]].copy()
    ww["per_capita_usgal_day"] = pd.to_numeric(ww["per_capita_usgal_day"], errors="coerce").fillna(0.0)

    df = rooms.merge(ash, how="left", left_on="occupancy_category", right_on="Occupancy Category")
    df = df.merge(ww, how="left", on="wastewater_category")

    df["Default Occupant Density"] = df["Default Occupant Density"].fillna(0.0)
    df["per_capita_usgal_day"] = df["per_capita_usgal_day"].fillna(0.0)

    # ASHRAE default density is persons / 1000 ft². If persons are entered, persons win.
    df["area_based_persons"] = (df["area_ft2"] / 1000.0) * df["Default Occupant Density"] * df["qty"]
    df["person_based_persons"] = df["persons_per_room"] * df["qty"]
    df["input_warning"] = ""
    df.loc[(df["area_ft2"] > 0) & (df["persons_per_room"] > 0), "input_warning"] = (
        "Both area and persons entered; persons used."
    )
    df["daily_peak_occupancy"] = df["person_based_persons"].where(
        df["persons_per_room"] > 0, df["area_based_persons"]
    )
    df["adwf_usgal_day"] = df["daily_peak_occupancy"] * df["per_capita_usgal_day"]
    df["adwf_m3_day"] = df["adwf_usgal_day"] / USGAL_PER_M3

    building_summary = (
        df.groupby("building", dropna=False)
        .agg(
            daily_peak_occupancy=("daily_peak_occupancy", "sum"),
            adwf_usgal_day=("adwf_usgal_day", "sum"),
            adwf_m3_day=("adwf_m3_day", "sum"),
        )
        .reset_index()
        .sort_values("building")
    )

    total_population = float(df["daily_peak_occupancy"].sum())
    total_adwf_usgal = float(df["adwf_usgal_day"].sum())
    total_adwf_m3 = float(df["adwf_m3_day"].sum())
    pf = harmon_peak_factor(total_population)

    if not building_summary.empty:
        building_summary["harmon_peak_factor"] = pf
        building_summary["peak_swf_usgal_day"] = building_summary["adwf_usgal_day"] * pf
        building_summary["peak_swf_usgal_hr"] = building_summary["peak_swf_usgal_day"] / 24.0

    sewage_storage_usgal = total_adwf_usgal * settings.sewage_retention_days if settings.sewage_storage_enabled else 0.0
    potable_storage_usgal = total_adwf_usgal * settings.potable_storage_days if settings.potable_storage_enabled else 0.0
    flushing_usgal = total_adwf_usgal * settings.flushing_percent / 100.0

    return {
        "room_calcs": df,
        "building_summary": building_summary,
        "daily_peak_occupancy": total_population,
        "adwf_usgal_day": total_adwf_usgal,
        "adwf_m3_day": total_adwf_m3,
        "potable_usgal_day": total_adwf_usgal,
        "potable_storage_usgal": potable_storage_usgal,
        "sewage_storage_usgal": sewage_storage_usgal,
        "flushing_usgal_day": flushing_usgal,
        "harmon_peak_factor": pf,
        "peak_swf_usgal_day": total_adwf_usgal * pf,
        "peak_swf_usgal_hr": (total_adwf_usgal * pf) / 24.0 if total_adwf_usgal else 0.0,
        "settings": asdict(settings),
    }


def starter_rooms() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "building": "Demo Building A",
                "room_type": "Classroom",
                "area_ft2": 850,
                "occupancy_category": "Classrooms (age 9 plus)",
                "qty": 4,
                "persons_per_room": 0,
                "wastewater_category": "School / student",
            },
            {
                "building": "Demo Building A",
                "room_type": "Office",
                "area_ft2": 300,
                "occupancy_category": "Office space",
                "qty": 2,
                "persons_per_room": 0,
                "wastewater_category": "Office / staff",
            },
            {
                "building": "Demo Building B",
                "room_type": "Dining",
                "area_ft2": 1200,
                "occupancy_category": "Cafeteria/fast-food dining",
                "qty": 1,
                "persons_per_room": 0,
                "wastewater_category": "Kitchen / cafeteria",
            },
        ]
    )
