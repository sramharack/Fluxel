from __future__ import annotations

import math


def round_diameter_from_cfm_velocity(cfm: float, velocity_fpm: float) -> float:
    """Return round duct diameter in inches."""
    if cfm <= 0 or velocity_fpm <= 0:
        return 0.0
    area_ft2 = cfm / velocity_fpm
    diameter_ft = math.sqrt((4.0 * area_ft2) / math.pi)
    return diameter_ft * 12.0


def velocity_from_cfm_diameter(cfm: float, diameter_in: float) -> float:
    if cfm <= 0 or diameter_in <= 0:
        return 0.0
    diameter_ft = diameter_in / 12.0
    area_ft2 = math.pi * diameter_ft**2 / 4.0
    return cfm / area_ft2


def round_diameter_from_cfm_friction(cfm: float, friction_inwg_per_100ft: float) -> float:
    """Approximate round duct diameter in inches using common duct friction form."""
    if cfm <= 0 or friction_inwg_per_100ft <= 0:
        return 0.0
    return (0.109136 * (cfm**1.9) / friction_inwg_per_100ft) ** (1.0 / 5.02)


def equivalent_round_rectangular(width_in: float, height_in: float) -> float:
    if width_in <= 0 or height_in <= 0:
        return 0.0
    return 1.3 * ((width_in * height_in) ** 0.625) / ((width_in + height_in) ** 0.25)
