
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


def _html_cell(text: str, bold: bool = False, bgcolor: str | None = "#FFFFFF", align: str = "CENTER") -> str:
    """Small helper for Graphviz HTML-like node labels."""
    import html

    safe = html.escape(str(text), quote=False).replace("\n", "<BR/>")
    if bold:
        safe = f"<B>{safe}</B>"
    bg = f' BGCOLOR="{bgcolor}"' if bgcolor else ""
    return f'<TR><TD{bg} ALIGN="{align}">{safe}</TD></TR>'


def _flow_node(title: str, lines: list[str] | None = None, header_bg: str = "#E5E7EB", width: int = 170) -> str:
    """Return a professional block-flow node using a Graphviz HTML table."""
    body = [_html_cell(title, bold=True, bgcolor=header_bg)]
    for line in lines or []:
        if line not in (None, ""):
            body.append(_html_cell(line))
    rows = "".join(body)
    return (
        f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="7" WIDTH="{width}">'
        f'{rows}'
        f'</TABLE>>'
    )


def _flow_setting(settings: dict, key: str, default):
    value = settings.get(key, default)
    return default if value in (None, "") else value


def make_flow_diagram_dot(results: dict) -> str:
    """
    Return an engineering-style site flow chart in DOT format.

    This intentionally uses a block-flow representation instead of a Sankey chart.
    It is meant to look close to the Excel engineering sketch:
    source -> treatment -> storage -> consumption -> wastewater -> septic -> disposal,
    with optional rainwater/flushing shown as a separate branch.
    """
    t = results.get("totals", {})
    settings = results.get("settings", {})
    name = results.get("project_name", "Site") or "Site"

    potable_day = float(t.get("Potable Demand USgal/day", 0) or 0)
    potable_m3_day = float(t.get("Potable Demand m3/day", 0) or 0)
    potable_storage = float(t.get("Potable Storage USgal", 0) or 0)
    potable_storage_m3 = float(t.get("Potable Storage m3", 0) or 0)

    wastewater_day = float(t.get("ADWF USgal/day", 0) or 0)
    wastewater_m3_day = float(t.get("ADWF m3/day", 0) or 0)
    sewage_storage = float(t.get("Sewage Storage USgal", 0) or 0)
    hourly_peak = float(t.get("Hourly Peak SWF USgal/hr", 0) or 0)
    rainwater = float(t.get("Rainwater Flushing USgal/day", 0) or 0)
    rainwater_m3_day = rainwater * USGAL_TO_LITRES / LITRES_PER_M3

    include_sewage = bool(settings.get("include_sewage_storage", True))
    include_potable = bool(settings.get("include_potable_storage", True))
    rainwater_enabled = bool(settings.get("include_rainwater_branch", rainwater > 0)) and rainwater > 0

    sewage_days = float(settings.get("sewage_retention_days", 0) or 0)
    potable_days = float(settings.get("potable_storage_days", 0) or 0)
    rainwater_pct = float(settings.get("rainwater_flushing_percent", 0) or 0)

    source_label = _flow_setting(settings, "potable_source_label", "B.W.A.")
    filter_label = _flow_setting(settings, "water_filter_label", "Water filter")
    rain_source_label = _flow_setting(settings, "rainwater_source_label", "Rain water")
    rain_suck_label = _flow_setting(settings, "rainwater_suck_wells_label", "Rain water suck wells")
    septic_label = _flow_setting(settings, "septic_tanks_label", "Septic tanks")
    disposal_label = _flow_setting(settings, "sewage_suck_wells_label", "Sewage suck wells")

    water_filter_qty = int(float(_flow_setting(settings, "water_filter_qty", 1)))
    potable_storage_qty = int(float(_flow_setting(settings, "potable_storage_qty", 1)))
    rain_suck_well_qty = int(float(_flow_setting(settings, "rainwater_suck_well_qty", 1)))
    septic_tank_qty = int(float(_flow_setting(settings, "septic_tank_qty", 1)))
    sewage_suck_well_qty = int(float(_flow_setting(settings, "sewage_suck_well_qty", 1)))

    def qty_line(qty: int, singular: str = "unit") -> str:
        return f"Qty: {qty:g} {singular}{'' if qty == 1 else 's'}" if qty and qty > 0 else ""

    def usgal_day(value: float) -> str:
        return f"{value:,.0f} USgal/day"

    def m3_day(value: float) -> str:
        return f"{value:,.2f} m³/day"

    def usgal(value: float) -> str:
        return f"{value:,.0f} USgal"

    title = f"Site Flow Chart — {name}"

    lines = [
        "digraph SiteFlow {",
        '  graph [rankdir=LR, bgcolor="#FFFFFF", pad=0.25, nodesep=0.65, ranksep=0.85, splines=ortho, outputorder=edgesfirst];',
        '  graph [fontname="Arial", fontsize=14, labelloc=t, labeljust=l, label="' + title.replace('"', "'") + '"];',
        '  node [shape=plain, fontname="Arial", fontsize=11];',
        '  edge [color="#111827", fontname="Arial", fontsize=9, arrowsize=0.8, penwidth=1.25];',
        "",
        f'  Source [label={_flow_node("Source", [str(source_label), usgal_day(potable_day)], "#E5E7EB", 165)}];',
        f'  Filter [label={_flow_node(str(filter_label), [qty_line(water_filter_qty)], "#E5E7EB", 195)}];',
    ]

    if include_potable:
        storage_title = f"{potable_days:g} Day Storage" if potable_days else "Potable Storage"
        lines.append(
            f'  PotableStorage [label={_flow_node(storage_title, [qty_line(potable_storage_qty, "tank"), usgal(potable_storage), f"{potable_storage_m3:,.2f} m³"], "#E5E7EB", 185)}];'
        )

    lines.extend([
        f'  Consumption [label={_flow_node("Consumption", [usgal_day(potable_day), m3_day(potable_m3_day)], "#E5E7EB", 170)}];',
        f'  Wastewater [label={_flow_node("Wastewater", [m3_day(wastewater_m3_day), usgal_day(wastewater_day), f"Peak: {hourly_peak:,.0f} USgal/hr"], "#E5E7EB", 170)}];',
    ])

    if rainwater_enabled:
        lines.extend([
            f'  RainSource [label={_flow_node("Source", [str(rain_source_label)], "#E5E7EB", 165)}];',
            f'  RainSuck [label={_flow_node(str(rain_suck_label), [qty_line(rain_suck_well_qty, "well")], "#E5E7EB", 195)}];',
            f'  Flushing [label={_flow_node(f"Flushing - {rainwater_pct:g}% wastewater", [usgal_day(rainwater), m3_day(rainwater_m3_day)], "#E5E7EB", 175)}];',
        ])

    if include_sewage:
        lines.append(
            f'  Septic [label={_flow_node(str(septic_label), [qty_line(septic_tank_qty, "tank"), f"Retention: {sewage_days:g} day(s)", usgal(sewage_storage)], "#E5E7EB", 180)}];'
        )
    lines.append(
        f'  Disposal [label={_flow_node(str(disposal_label), [qty_line(sewage_suck_well_qty, "well")], "#E5E7EB", 180)}];'
    )

    # Main potable-to-wastewater path.
    lines.append("")
    lines.append("  Source -> Filter;")
    if include_potable:
        lines.append("  Filter -> PotableStorage;")
        lines.append("  PotableStorage -> Consumption;")
    else:
        lines.append("  Filter -> Consumption;")
    lines.append("  Consumption -> Wastewater;")

    # Wastewater treatment/disposal path.
    if include_sewage:
        lines.append("  Wastewater -> Septic;")
        lines.append("  Septic -> Disposal;")
    else:
        lines.append("  Wastewater -> Disposal;")

    # Optional rainwater/flushing branch.
    if rainwater_enabled:
        lines.append("")
        lines.append("  RainSource -> RainSuck;")
        lines.append("  RainSuck -> Flushing;")
        if include_sewage:
            lines.append("  Flushing -> Septic;")
        else:
            lines.append("  Flushing -> Disposal;")

    # Column alignment keeps the rainwater branch beneath the matching potable process blocks.
    # With rankdir=LR, rank=same means same vertical column.
    lines.append("")
    if rainwater_enabled:
        lines.append("  { rank=same; Source; RainSource; }")
        lines.append("  { rank=same; Filter; RainSuck; }")
        lines.append("  { rank=same; Consumption; Flushing; }")
    if include_sewage:
        lines.append("  { rank=same; Wastewater; Septic; }")

    lines.append("}")
    return "\n".join(lines)
