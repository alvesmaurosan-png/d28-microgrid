"""Conditional R1 CHP capital and fixed operating costs.

Exploratory accounting in real BRL.
No scientific or tariff homologation is implied.
Fuel, contingency and lifecycle emissions are excluded.
"""

from __future__ import annotations

import math


def _nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def chp_capital_present_value(
    capacity_kw: float,
    capex_brl_per_kw: float,
    fixed_opex_fraction_year: float,
    overhaul_fraction: float,
    *,
    overhaul_year: int,
    discount_rate_real_year: float,
    horizon_years: int,
) -> dict:
    """Return CHP capital, annual fixed OPEX and discounted costs."""

    capacity = _nonnegative("capacity_kw", capacity_kw)
    unit_capex = _nonnegative("capex_brl_per_kw", capex_brl_per_kw)
    opex_fraction = _nonnegative(
        "fixed_opex_fraction_year", fixed_opex_fraction_year
    )
    overhaul_fraction = _nonnegative(
        "overhaul_fraction", overhaul_fraction
    )
    rate = _nonnegative(
        "discount_rate_real_year", discount_rate_real_year
    )

    if type(horizon_years) is not int or horizon_years < 1:
        raise ValueError("horizon_years must be a positive integer")

    if type(overhaul_year) is not int or overhaul_year < 1:
        raise ValueError("overhaul_year must be a positive integer")

    capex = capacity * unit_capex
    annual_opex = capex * opex_fraction

    annuity = sum(
        (1 + rate) ** (-year)
        for year in range(1, horizon_years + 1)
    )

    overhaul_cost = capex * overhaul_fraction

    overhaul_pv = (
        overhaul_cost / (1 + rate) ** overhaul_year
        if overhaul_year <= horizon_years
        else 0.0
    )

    return {
        "chp_capex_brl": capex,
        "chp_annual_fixed_opex_brl": annual_opex,
        "chp_overhaul_cost_brl": overhaul_cost,
        "chp_overhaul_present_value_brl": overhaul_pv,
        "annuity_factor": annuity,
        "chp_capital_fixed_present_value_brl": (
            capex + annual_opex * annuity + overhaul_pv
        ),
    }
