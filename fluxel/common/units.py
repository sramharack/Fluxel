USGAL_PER_M3 = 264.172052
M3_PER_USGAL = 1 / USGAL_PER_M3


def m3_day_to_usgal_day(value_m3_day: float) -> float:
    return value_m3_day * USGAL_PER_M3


def usgal_day_to_m3_day(value_usgal_day: float) -> float:
    return value_usgal_day * M3_PER_USGAL


def sqft_to_sqm(value_sqft: float) -> float:
    return value_sqft * 0.09290304


def sqm_to_sqft(value_sqm: float) -> float:
    return value_sqm / 0.09290304
