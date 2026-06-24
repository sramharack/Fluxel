from __future__ import annotations

from html import escape


def _box(x: int, y: int, w: int, h: int, title: str, lines: list[str] | None = None) -> str:
    lines = lines or []
    title = escape(title)
    text = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="0" fill="#f2f2f2" stroke="#111" stroke-width="1.2"/>',
        f'<text x="{x + w/2}" y="{y + 28}" font-size="14" font-weight="600" text-anchor="middle">{title}</text>',
    ]
    yy = y + 50
    for line in lines:
        text.append(f'<text x="{x + w/2}" y="{yy}" font-size="12" text-anchor="middle">{escape(line)}</text>')
        yy += 18
    return "\n".join(text)


def _arrow(x1: int, y1: int, x2: int, y2: int) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#111" stroke-width="1.8" marker-end="url(#arrow)"/>'


def _poly(points: list[tuple[int, int]]) -> str:
    d = "M " + " L ".join(f"{x} {y}" for x, y in points)
    return f'<path d="{d}" fill="none" stroke="#111" stroke-width="1.8" marker-end="url(#arrow)"/>'


def make_site_flow_svg(results: dict, equipment: dict | None = None) -> str:
    """Return a deterministic engineering block-flow SVG.

    This avoids Graphviz routing issues. Coordinates are fixed so arrows land on box edges.
    """
    equipment = equipment or {}
    potable_usgpd = results.get("potable_usgal_day", results.get("adwf_usgal_day", 0.0))
    wastewater_usgpd = results.get("adwf_usgal_day", 0.0)
    wastewater_m3d = results.get("adwf_m3_day", 0.0)
    flushing_usgpd = results.get("flushing_usgal_day", 0.0)
    potable_storage = results.get("potable_storage_usgal", potable_usgpd)
    sewage_storage = results.get("sewage_storage_usgal", 0.0)

    title = escape(results.get("project_name", "Site Flow Chart"))
    water_filter_qty = equipment.get("water_filter_qty", 1)
    septic_qty = equipment.get("septic_tank_qty", 1)
    sewage_well_qty = equipment.get("sewage_well_qty", 1)
    rainwater_well_qty = equipment.get("rainwater_well_qty", 1)

    svg = f'''
<svg viewBox="0 0 1180 620" width="100%" height="620" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#111" />
    </marker>
    <style>
      text {{ font-family: Arial, Helvetica, sans-serif; fill: #111; }}
      .small {{ font-size: 12px; }}
      .label {{ font-size: 13px; font-style: italic; }}
    </style>
  </defs>
  <rect x="0" y="0" width="1180" height="620" fill="white"/>
  <text x="24" y="32" font-size="18" font-weight="700">3.3 Site Flow Chart</text>
  <text x="24" y="68" class="label">Total Potable Water Flow:</text>
  <text x="250" y="68" class="label" fill="#005bbb">{title}</text>

  {_box(24, 88, 170, 92, "Source", ["B.W.A."])}
  {_box(254, 88, 210, 92, "Water Filter", [f"Qty: {water_filter_qty}"])}
  {_box(534, 88, 210, 92, "Potable Storage", [f"{potable_storage:,.0f} USgal"])}
  {_box(814, 88, 140, 92, "Consumption", [f"{potable_usgpd:,.0f} USgal/day"])}
  {_box(1010, 88, 145, 92, "Wastewater", [f"{wastewater_m3d:,.1f} m³/day", f"{wastewater_usgpd:,.0f} USgal/day"])}

  {_box(24, 230, 170, 92, "Source", ["Rain Water"])}
  {_box(254, 230, 210, 92, "Rainwater", ["Suck Wells", f"Qty: {rainwater_well_qty}"])}

  {_box(814, 230, 140, 100, "Flushing", ["30% wastewater", f"{flushing_usgpd:,.0f} USgal/day"])}
  {_box(1010, 365, 145, 92, "Septic Tanks", [f"Qty: {septic_qty}", f"{sewage_storage:,.0f} USgal"])}
  {_box(1010, 495, 145, 92, "Sewage", ["Suck Wells", f"Qty: {sewage_well_qty}"])}

  {_arrow(194, 134, 254, 134)}
  {_arrow(464, 134, 534, 134)}
  {_arrow(744, 134, 814, 134)}
  {_arrow(954, 134, 1010, 134)}

  {_arrow(194, 276, 254, 276)}
  {_poly([(884, 180), (884, 230)])}
  {_poly([(884, 330), (884, 411), (1010, 411)])}
  {_poly([(1082, 180), (1082, 365)])}
  {_arrow(1082, 457, 1082, 495)}
</svg>'''
    return svg
