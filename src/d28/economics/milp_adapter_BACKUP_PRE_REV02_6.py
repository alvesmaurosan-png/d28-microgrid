"""Opt-in Pyomo adapter. Leaves existing build_r0_milp unchanged."""
from __future__ import annotations
from collections import Counter
from typing import Sequence
from .f1 import Economics, capital_and_fixed_opex, month_groups, present_value


def attach_economic_objective(model, cfg: Economics, *, pv_kwp: float,
                              bess_kwh: float, pcs_kw: float,
                              months: Sequence[int], dt_hours: float,
                              annual_pkm: float | None = None):
    """Attach annual bill and 20-year F1 to an *unsolved* R0 model.

    This is an opt-in replacement objective for dispatch given fixed design.
    It does not optimize the three design capacities, nor F2, nor F3.
    Calendar months must correspond exactly to model time index and dt_hours.
    """
    import pyomo.environ as p
    if hasattr(model, "m31_cost_objective"):
        raise ValueError("M3.1 objective already attached")
    if not hasattr(model, "grid") or not hasattr(model, "obj"):
        raise ValueError("Expected build_r0_milp model with grid and obj")
    n = len(model.T)
    if len(months) != n or n < 1:
        raise ValueError("month vector length must equal model horizon")
    if not 0 < dt_hours <= 1:
        raise ValueError("dt_hours must be in (0,1]")
    if hasattr(model, "_r0_metadata") and abs(
        model._r0_metadata.get("dt_hours", dt_hours) - dt_hours) > 1e-12:
        raise ValueError("dt_hours disagrees with original model")
    cap = capital_and_fixed_opex(cfg, pv_kwp, bess_kwh, pcs_kw)
    month_keys = sorted(set(months))
    if any(not isinstance(x, int) or x % 100 not in range(1, 13) for x in month_keys):
        raise ValueError("invalid month YYYYMM")
    # This model's fixed annual cashflow scenario requires all 12 months.
    if len(month_keys) != 12 or len({m // 100 for m in month_keys}) != 1:
        raise ValueError("full 12-month calendar required for annualized F1")
    month_by_t = dict(enumerate(months))
    model.m31_months = p.Set(initialize=month_keys, ordered=True)
    model.m31_monthly_peak = p.Var(model.m31_months,
                                  domain=p.NonNegativeReals,
                                  bounds=(0, cfg.pcc_import_limit_kw))
    model.m31_peak_bound = p.Constraint(
        model.T, rule=lambda m, t:
        m.grid[t] <= m.m31_monthly_peak[month_by_t[t]])
    model.m31_energy_kwh = p.Expression(expr=dt_hours * sum(model.grid[t] for t in model.T))
    model.m31_energy_cost_brl = p.Expression(
        expr=cfg.energy_tariff_brl_per_kwh * model.m31_energy_kwh)
    model.m31_demand_cost_brl = p.Expression(
        expr=cfg.demand_tariff_brl_per_kw_month
        * sum(model.m31_monthly_peak[m] for m in model.m31_months))
    # For a single representative year, repeat identical costs annually.
    # No load growth, tariff escalation, degradation or re-optimization assumed.
    annuity = sum((1 + cfg.discount_rate_real_year) ** (-y)
                 for y in range(1, cfg.horizon_years + 1))
    fixed_pv = present_value(cfg, pv_kwp, bess_kwh, pcs_kw)
    model.m31_pv_cost_brl = p.Expression(
        expr=fixed_pv["pv_cost_without_variable_bill_brl"]
        + annuity * (model.m31_energy_cost_brl + model.m31_demand_cost_brl))
    if annual_pkm is not None:
        if annual_pkm <= 0:
            raise ValueError("annual_pkm must be > 0")
        model.m31_f1_brl_per_pkm = p.Expression(
            expr=model.m31_pv_cost_brl / (annual_pkm * annuity))
    model.obj.deactivate()
    model.m31_cost_objective = p.Objective(expr=model.m31_pv_cost_brl, sense=p.minimize)
    return model
