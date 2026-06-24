
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple
import math

USGAL_TO_LITRES = 3.785411784
LITRES_PER_M3 = 1000.0


def to_float(value: Any, default: float | None = None) -> float | None:
    """Convert common form values to float while treating blanks and '-' as missing."""
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        if math.isnan(value) if isinstance(value, float) else False:
            return default
        return float(value)
    text = str(value).strip()
    if text in ("", "-", "—", "None", "nan", "NaN"):
        return default
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return default


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def harmon_peak_factor(population: float) -> float:
    """
    Harmon peaking factor.

    P is the contributing population. The workbook used population / 1000 inside
    the square root: 1 + 14 / (4 + sqrt(P / 1000)).
    """
    population = to_float(population, 0.0) or 0.0
    if population <= 0:
        return 0.0
    return 1.0 + 14.0 / (4.0 + math.sqrt(population / 1000.0))


def build_lookup(rows: Iterable[dict], key: str = "category") -> Dict[str, dict]:
    result = {}
    for row in rows:
        name = clean_text(row.get(key))
        if name:
            result[name] = dict(row)
    return result


def ashrae_density_capita_per_ft2(ashrae_row: dict | None) -> float:
    if not ashrae_row:
        return 0.0
    density_per_1000 = to_float(ashrae_row.get("default_occupant_density_per_1000_ft2"), 0.0) or 0.0
    return density_per_1000 / 1000.0


def room_calculation(
    room: dict,
    ashrae_lookup: Dict[str, dict],
    wastewater_lookup: Dict[str, dict],
) -> dict:
    """Calculate one room row. UI fields remain intentionally simple."""
    method = clean_text(room.get("input_method")) or "Persons"
    room_type = clean_text(room.get("room_type"))
    qty = to_float(room.get("quantity"), 0.0) or 0.0
    area = to_float(room.get("area_ft2"), None)
    persons = to_float(room.get("persons_per_room"), None)
    manual_density = to_float(room.get("manual_density_capita_per_ft2"), None)
    manual_per_cap_usgal = to_float(room.get("manual_per_capita_usgal_day"), None)
    ashrae_category = clean_text(room.get("ashrae_occupancy_category"))
    wastewater_category = clean_text(room.get("wastewater_category"))

    warnings: list[str] = []
    errors: list[str] = []

    if not room_type:
        warnings.append("Room type is blank.")

    if method not in ("Area", "Persons"):
        warnings.append(f"Unknown input method '{method}'. Treated as Persons.")
        method = "Persons"

    if method == "Area":
        if area is None or area <= 0:
            # Allow placeholder/zero rows without raising errors.
            if qty > 0:
                errors.append("Area method selected but area_ft2 is missing or zero.")
            daily_peak_occ = 0.0
            occupant_density = 0.0
        else:
            if manual_density is not None and manual_density > 0:
                occupant_density = manual_density
                density_source = "Manual"
            else:
                occupant_density = ashrae_density_capita_per_ft2(ashrae_lookup.get(ashrae_category))
                density_source = "ASHRAE 62.1 Table 6-1"
                if occupant_density <= 0 and ashrae_category and qty > 0:
                    warnings.append("ASHRAE occupant density is zero for selected category.")
                if not ashrae_category and qty > 0:
                    errors.append("Area method selected but ASHRAE occupancy category is blank.")
            if persons not in (None, 0):
                warnings.append("Persons value was entered but ignored because method is Area.")
            daily_peak_occ = (area or 0.0) * qty * occupant_density
    else:
        density_source = "Manual persons"
        occupant_density = persons if persons is not None else 0.0
        # Allow placeholder rows where qty is blank/zero.
        if persons is None and qty > 0:
            if wastewater_category:
                errors.append("Persons method selected but persons_per_room is missing.")
            else:
                warnings.append("No persons and no wastewater category; row treated as zero flow.")
        if area not in (None, 0):
            warnings.append("Area value was entered but ignored because method is Persons.")
        daily_peak_occ = (persons or 0.0) * qty

    waste_row = wastewater_lookup.get(wastewater_category)
    if manual_per_cap_usgal is not None and manual_per_cap_usgal >= 0:
        per_cap_usgal = manual_per_cap_usgal
        per_cap_source = "Manual"
    elif waste_row:
        per_cap_usgal = to_float(waste_row.get("usgal_per_capita_day"), 0.0) or 0.0
        per_cap_source = "Corbitt/workbook category"
    else:
        per_cap_usgal = 0.0
        per_cap_source = "None"
        if daily_peak_occ > 0:
            warnings.append("Wastewater category is blank or not found; per-capita wastewater flow set to zero.")

    per_cap_l = per_cap_usgal * USGAL_TO_LITRES
    adwf_usgal_day = daily_peak_occ * per_cap_usgal
    adwf_m3_day = daily_peak_occ * per_cap_l / LITRES_PER_M3

    return {
        **room,
        "input_method": method,
        "quantity": qty,
        "area_ft2": area,
        "persons_per_room": persons,
        "occupant_density_capita_per_ft2_or_person": occupant_density,
        "occupant_density_source": density_source,
        "daily_peak_occupancy": daily_peak_occ,
        "per_capita_wastewater_l_day": per_cap_l,
        "per_capita_wastewater_usgal_day": per_cap_usgal,
        "per_capita_source": per_cap_source,
        "adwf_m3_day": adwf_m3_day,
        "adwf_usgal_day": adwf_usgal_day,
        "warnings": warnings,
        "errors": errors,
    }


def building_calculation(building: dict, ashrae_lookup: Dict[str, dict], wastewater_lookup: Dict[str, dict]) -> dict:
    rooms = [room_calculation(r, ashrae_lookup, wastewater_lookup) for r in building.get("rooms", [])]
    total_population = sum(to_float(r.get("daily_peak_occupancy"), 0.0) or 0.0 for r in rooms)
    total_m3 = sum(to_float(r.get("adwf_m3_day"), 0.0) or 0.0 for r in rooms)
    total_usgal = sum(to_float(r.get("adwf_usgal_day"), 0.0) or 0.0 for r in rooms)
    errors = [f"{r.get('room_type','Room')}: {e}" for r in rooms for e in r.get("errors", [])]
    warnings = [f"{r.get('room_type','Room')}: {w}" for r in rooms for w in r.get("warnings", [])]
    return {
        "building_id": building.get("building_id", ""),
        "description": building.get("description", ""),
        "rooms": rooms,
        "daily_peak_occupancy": total_population,
        "adwf_m3_day": total_m3,
        "adwf_usgal_day": total_usgal,
        "warnings": warnings,
        "errors": errors,
        "workbook_totals": building.get("workbook_totals", {}),
    }


def project_calculation(project: dict, ashrae_rows: list[dict], wastewater_rows: list[dict]) -> dict:
    settings = project.get("settings", {})
    include_sewage_storage = bool(settings.get("include_sewage_storage", True))
    include_potable_storage = bool(settings.get("include_potable_storage", True))
    sewage_days = to_float(settings.get("sewage_retention_days"), 0.0) or 0.0
    potable_days = to_float(settings.get("potable_storage_days"), 0.0) or 0.0
    rainwater_pct = to_float(settings.get("rainwater_flushing_percent"), 0.0) or 0.0

    ashrae_lookup = build_lookup(ashrae_rows, "occupancy_category")
    wastewater_lookup = build_lookup(wastewater_rows, "category")

    buildings = [building_calculation(b, ashrae_lookup, wastewater_lookup) for b in project.get("buildings", [])]
    site_population = sum(b["daily_peak_occupancy"] for b in buildings)
    site_adwf_m3 = sum(b["adwf_m3_day"] for b in buildings)
    site_adwf_usgal = sum(b["adwf_usgal_day"] for b in buildings)
    pf = harmon_peak_factor(site_population)

    summaries = []
    for b in buildings:
        avg_usgal = b["adwf_usgal_day"]
        avg_m3 = b["adwf_m3_day"]
        summaries.append({
            "Location": b["building_id"],
            "Description": b.get("description", ""),
            "Daily Peak Occupancy": b["daily_peak_occupancy"],
            "ADWF m3/day": avg_m3,
            "ADWF USgal/day": avg_usgal,
            "Sewage Storage USgal": avg_usgal * sewage_days if include_sewage_storage else 0.0,
            "Harmon Peak Factor": pf,
            "Hourly Peak SWF m3/hr": avg_m3 * pf / 24.0 if avg_m3 else 0.0,
            "Hourly Peak SWF USgal/hr": avg_usgal * pf / 24.0 if avg_usgal else 0.0,
            "Potable Demand m3/day": avg_m3,
            "Potable Demand USgal/day": avg_usgal,
            "Potable Storage m3": avg_m3 * potable_days if include_potable_storage else 0.0,
            "Potable Storage USgal": avg_usgal * potable_days if include_potable_storage else 0.0,
        })

    totals = {
        "Daily Peak Occupancy": site_population,
        "ADWF m3/day": site_adwf_m3,
        "ADWF USgal/day": site_adwf_usgal,
        "Sewage Storage USgal": site_adwf_usgal * sewage_days if include_sewage_storage else 0.0,
        "Harmon Peak Factor": pf,
        "Hourly Peak SWF m3/hr": site_adwf_m3 * pf / 24.0 if site_adwf_m3 else 0.0,
        "Hourly Peak SWF USgal/hr": site_adwf_usgal * pf / 24.0 if site_adwf_usgal else 0.0,
        "Potable Demand m3/day": site_adwf_m3,
        "Potable Demand USgal/day": site_adwf_usgal,
        "Potable Storage m3": site_adwf_m3 * potable_days if include_potable_storage else 0.0,
        "Potable Storage USgal": site_adwf_usgal * potable_days if include_potable_storage else 0.0,
        "Rainwater Flushing USgal/day": site_adwf_usgal * rainwater_pct / 100.0,
    }

    errors = [f"{b['building_id']} - {e}" for b in buildings for e in b.get("errors", [])]
    warnings = [f"{b['building_id']} - {w}" for b in buildings for w in b.get("warnings", [])]

    return {
        "project_name": project.get("project_name", ""),
        "project_location": project.get("project_location", ""),
        "settings": settings,
        "buildings": buildings,
        "summary_rows": summaries,
        "totals": totals,
        "warnings": warnings,
        "errors": errors,
    }


def comparison_to_workbook(results: dict) -> list[dict]:
    """Compare calculated building totals to extracted workbook totals when seed data contains those totals."""
    rows = []
    for b in results.get("buildings", []):
        wb_tot = b.get("workbook_totals") or {}
        if not wb_tot:
            continue
        rows.append({
            "Location": b.get("building_id"),
            "Calc Occupancy": b.get("daily_peak_occupancy"),
            "Workbook Occupancy": wb_tot.get("daily_peak_occupancy"),
            "Δ Occupancy": (b.get("daily_peak_occupancy") or 0) - (wb_tot.get("daily_peak_occupancy") or 0),
            "Calc ADWF USgal/day": b.get("adwf_usgal_day"),
            "Workbook ADWF USgal/day": wb_tot.get("adwf_usgal_day"),
            "Δ ADWF USgal/day": (b.get("adwf_usgal_day") or 0) - (wb_tot.get("adwf_usgal_day") or 0),
        })
    return rows


def make_flow_diagram_dot(results: dict) -> str:
    """Return a clean block-flow diagram in DOT format for Streamlit's graphviz_chart."""
    t = results.get("totals", {})
    settings = results.get("settings", {})
    name = results.get("project_name", "Site") or "Site"
    potable_day = t.get("Potable Demand USgal/day", 0) or 0
    potable_storage = t.get("Potable Storage USgal", 0) or 0
    sewage_day = t.get("ADWF USgal/day", 0) or 0
    sewage_m3 = t.get("ADWF m3/day", 0) or 0
    sewage_storage = t.get("Sewage Storage USgal", 0) or 0
    hourly_peak = t.get("Hourly Peak SWF USgal/hr", 0) or 0
    rainwater = t.get("Rainwater Flushing USgal/day", 0) or 0
    include_sewage = bool(settings.get("include_sewage_storage", True))
    include_potable = bool(settings.get("include_potable_storage", True))
    sewage_days = settings.get("sewage_retention_days", 0)
    potable_days = settings.get("potable_storage_days", 0)

    def label(title: str, *lines: str) -> str:
        parts = [title] + [x for x in lines if x]
        return "\\n".join(parts).replace('"', "'")

    storage_node = "PotableStorage" if include_potable else "Buildings"
    sewage_storage_node = "SepticStorage" if include_sewage else "SewageDisposal"

    lines = [
        "digraph G {",
        "  graph [rankdir=LR, bgcolor=transparent, pad=0.2, nodesep=0.55, ranksep=0.75];",
        '  node [shape=box, style="rounded,filled", color="#334155", fillcolor="#F8FAFC", fontname="Arial", fontsize=11, margin=0.12];',
        '  edge [color="#334155", fontname="Arial", fontsize=10, arrowsize=0.8];',
        f'  Source [label="{label("B.W.A. / potable source", f"{potable_day:,.0f} USgal/day")}", fillcolor="#EFF6FF"];',
        '  Filter [label="Water treatment / filtration", fillcolor="#EFF6FF"];',
    ]
    if include_potable:
        lines.append(f'  PotableStorage [label="{label("Potable water storage", f"{potable_storage:,.0f} USgal", f"{float(potable_days):g} day(s)")}", fillcolor="#DBEAFE"];')
    lines.extend([
        f'  Buildings [label="{label(name, f"{t.get("Daily Peak Occupancy",0):,.2f} people/day", f"{potable_day:,.0f} USgal/day")}", fillcolor="#F0FDFA"];',
        f'  Wastewater [label="{label("Wastewater generation", f"{sewage_m3:,.2f} m³/day", f"{sewage_day:,.0f} USgal/day", f"Peak: {hourly_peak:,.0f} USgal/hr")}", fillcolor="#FEF3C7"];'
    ])
    if include_sewage:
        lines.append(f'  SepticStorage [label="{label("Septic tank storage", f"{sewage_storage:,.0f} USgal", f"{float(sewage_days):g} day(s) retention")}", fillcolor="#FFEDD5"];')
    lines.append('  SewageDisposal [label="Sewage suck wells / disposal", fillcolor="#FEE2E2"];')
    if rainwater > 0:
        lines.extend([
            f'  Rainwater [label="{label("Rainwater source", f"{rainwater:,.0f} USgal/day allowance")}", fillcolor="#ECFEFF"];',
            '  Flushing [label="Non-potable flushing demand", fillcolor="#CFFAFE"];'
        ])
    lines.extend([
        '  Source -> Filter [label="potable supply"];',
    ])
    if include_potable:
        lines.append('  Filter -> PotableStorage;')
        lines.append('  PotableStorage -> Buildings [label="domestic water"];')
    else:
        lines.append('  Filter -> Buildings [label="domestic water"];')
    lines.append('  Buildings -> Wastewater [label="sanitary load"];')
    if include_sewage:
        lines.append('  Wastewater -> SepticStorage [label="retention"];')
        lines.append('  SepticStorage -> SewageDisposal;')
    else:
        lines.append('  Wastewater -> SewageDisposal;')
    if rainwater > 0:
        lines.append('  Rainwater -> Flushing;')
        lines.append('  Flushing -> Wastewater [label="adds to sewage load"];')
    lines.append("}")
    return "\n".join(lines)
