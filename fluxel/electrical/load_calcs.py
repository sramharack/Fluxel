from __future__ import annotations

import math


def three_phase_current(kva: float, voltage_ll: float) -> float:
    if voltage_ll <= 0:
        return 0.0
    return (kva * 1000.0) / (math.sqrt(3.0) * voltage_ll)


def kva_from_kw(kw: float, power_factor: float = 0.9) -> float:
    if power_factor <= 0:
        return 0.0
    return kw / power_factor


def demand_kw(connected_kw: float, demand_factor: float = 1.0, spare_percent: float = 0.0) -> float:
    return connected_kw * demand_factor * (1.0 + spare_percent / 100.0)
