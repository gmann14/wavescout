from __future__ import annotations

PRIMARY_SWELL_MIN_DEG = 120.0
PRIMARY_SWELL_MAX_DEG = 220.0


def is_primary_swell_facing(orientation_deg: float | None) -> bool:
    if orientation_deg is None:
        return False
    return PRIMARY_SWELL_MIN_DEG <= orientation_deg <= PRIMARY_SWELL_MAX_DEG


def coastal_exposure_class(exposure_arc_deg: float | None) -> str:
    if exposure_arc_deg is None:
        return "unknown"
    if exposure_arc_deg >= 120.0:
        return "open_coast"
    if exposure_arc_deg >= 90.0:
        return "outer_coast"
    if exposure_arc_deg >= 60.0:
        return "semi_sheltered"
    return "sheltered_inner_coast"


def coastal_context_penalty(
    exposure_arc_deg: float | None,
    orientation_deg: float | None,
    nearfield_open_water_deg: float | None = None,
    nearfield_blocked_ratio: float | None = None,
    farfield_open_water_deg: float | None = None,
    farfield_blocked_ratio: float | None = None,
) -> float:
    penalty = 0.0

    if exposure_arc_deg is None:
        penalty += 8.0
    elif exposure_arc_deg < 60.0:
        penalty += 24.0
    elif exposure_arc_deg < 90.0:
        penalty += 18.0
    elif exposure_arc_deg < 120.0:
        penalty += 8.0

    if not is_primary_swell_facing(orientation_deg):
        penalty += 10.0

    if nearfield_open_water_deg is not None:
        if nearfield_open_water_deg < 90.0:
            penalty += 14.0
        elif nearfield_open_water_deg < 110.0:
            penalty += 8.0

    if nearfield_blocked_ratio is not None:
        if nearfield_blocked_ratio >= 0.30:
            penalty += 10.0
        elif nearfield_blocked_ratio >= 0.15:
            penalty += 5.0

    # A segment can look open in the immediate 2 km fan while still sitting
    # deep inside a bay or estuary. The farther fan is the better proxy for
    # whether S/E ocean exposure really persists beyond the local mouth.
    if farfield_open_water_deg is not None:
        if farfield_open_water_deg < 70.0:
            penalty += 14.0
        elif farfield_open_water_deg < 90.0:
            penalty += 8.0

    if farfield_blocked_ratio is not None:
        if farfield_blocked_ratio >= 0.45:
            penalty += 8.0
        elif farfield_blocked_ratio >= 0.30:
            penalty += 4.0

    if (
        nearfield_open_water_deg is not None
        and farfield_open_water_deg is not None
        and nearfield_open_water_deg - farfield_open_water_deg >= 35.0
    ):
        penalty += 8.0

    return min(penalty, 28.0)
