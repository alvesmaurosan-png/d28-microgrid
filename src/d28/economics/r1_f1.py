"""M3.5-D — Conditional R1 F1 post-processing.

No MILP solve, no annual extrapolation and no scientific homologation.
CHP contingency is excluded pending documentary confirmation.
"""

from __future__ import annotations

import math

from .f1 import Economics, present_value
from .chp_capital import chp_capital_present_value


def _annual_cost(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def r1_present_value(
    cfg: Economics,
    *,
    pv_kwp: float,
    bess_kwh: float,
    pcs_kw: float,
    chp_capacity_kw: float,
    chp_capex_brl_per_kw: float,
    chp_fixed_opex_fraction_year: float,
    chp_overhaul_fraction: float,
    chp_overhaul_year: int,
    annual_grid_bill_brl: float | None = None,
    annual_fuel_cost_brl: float | None = None,
    annual_pkm: float | None = None,
) -> dict:
    """Consolidate R1 costs without inferring missing annual inputs."""

    grid = _annual_cost("annual_grid_bill_brl", annual_grid_bill_brl)
    fuel = _annual_cost("annual_fuel_cost_brl", annual_fuel_cost_brl)

    # R0 economic components, evaluated with the R1 grid bill.
    base = present_value(
        cfg,
        pv_kwp,
        bess_kwh,
        pcs_kw,
        annual_variable_bill_brl=grid,
        annual_pkm=annual_pkm,
    )

    chp = chp_capital_present_value(
        capacity_kw=chp_capacity_kw,
        capex_brl_per_kw=chp_capex_brl_per_kw,
        fixed_opex_fraction_year=chp_fixed_opex_fraction_year,
        overhaul_fraction=chp_overhaul_fraction,
        overhaul_year=chp_overhaul_year,
        discount_rate_real_year=cfg.discount_rate_real_year,
        horizon_years=cfg.horizon_years,
    )

    annuity = base["annuity_factor"]
    chp_fixed_pv = chp["chp_capital_fixed_present_value_brl"]

    result = {
        "architecture": "R1",
        "status": "EXPLORATORY_NOT_HOMOLOGATED",
        "annual_grid_bill_brl": grid,
        "annual_fuel_cost_brl": fuel,
        "r0_components": base,
        "chp_components": chp,
        "pv_cost_without_annual_variable_bills_brl": (
            base["pv_cost_without_variable_bill_brl"] + chp_fixed_pv
        ),
        "pv_total_cost_brl": None,
        "pv_pkm": base["pv_pkm"] if annual_pkm is not None else None,
        "f1_brl_per_pkm": None,
    }

    if grid is not None and fuel is not None:
        total = (
            base["pv_cost_without_variable_bill_brl"]
            + chp_fixed_pv
            + (grid + fuel) * annuity
        )
        result["pv_total_cost_brl"] = total

        if result["pv_pkm"] is not None:
            result["f1_brl_per_pkm"] = total / result["pv_pkm"]

    return result
