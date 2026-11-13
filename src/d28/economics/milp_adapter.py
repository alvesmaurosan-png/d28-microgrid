"""Opt-in Pyomo adapter. Leaves existing build_r0_milp unchanged."""
from __future__ import annotations
from collections import Counter
from typing import Sequence
from .f1 import Economics, capital_and_fixed_opex, month_groups, present_value, TariffPolicy, validate_tariff_calendar, annual_bill_regulated


def attach_economic_objective(model, cfg: Economics, *, pv_kwp: float,
                              bess_kwh: float, pcs_kw: float,
                              months: Sequence[int], dt_hours: float,
                              annual_pkm: float | None = None,
                              tariff_policy: TariffPolicy | None = None):
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
    if tariff_policy is None:
        model.m31_energy_cost_brl = p.Expression(
            expr=cfg.energy_tariff_brl_per_kwh * model.m31_energy_kwh)
        model.m31_demand_cost_brl = p.Expression(
            expr=cfg.demand_tariff_brl_per_kw_month
            * sum(model.m31_monthly_peak[m] for m in model.m31_months))
        annual_bill_expr = model.m31_energy_cost_brl + model.m31_demand_cost_brl
    else:
        validate_tariff_calendar(tariff_policy, months, n)
        model.m31_energy_cost_brl = p.Expression(expr=dt_hours * sum(
            model.grid[t] * tariff_policy.energy_tariffs_brl_per_kwh[t]
            for t in model.T))
        model.m31_additional_energy_cost_brl = p.Expression(expr=
            tariff_policy.additional_energy_charge_brl_per_kwh * model.m31_energy_kwh)
        model.m31_billed_demand = p.Var(model.m31_months, domain=p.NonNegativeReals)
        model.m31_billed_demand_lower_peak = p.Constraint(
            model.m31_months,
            rule=lambda m, month: m.m31_billed_demand[month] >= m.m31_monthly_peak[month])
        model.m31_billed_demand_lower_contract = p.Constraint(
            model.m31_months,
            rule=lambda m, month: m.m31_billed_demand[month] >=
            tariff_policy.contracted_demand_kw_by_month[month])
        model.m31_overrun_kw = p.Var(model.m31_months, domain=p.NonNegativeReals)
        model.m31_overrun_lower = p.Constraint(
            model.m31_months,
            rule=lambda m, month: m.m31_overrun_kw[month] >=
            m.m31_monthly_peak[month] -
            tariff_policy.overrun_threshold_multiplier *
            tariff_policy.contracted_demand_kw_by_month[month])
        model.m31_demand_cost_brl = p.Expression(expr=
            tariff_policy.demand_tariff_brl_per_kw_month *
            sum(model.m31_billed_demand[month] for month in model.m31_months))
        model.m31_overrun_cost_brl = p.Expression(expr=
            tariff_policy.overrun_tariff_brl_per_kw_month *
            sum(model.m31_overrun_kw[month] for month in model.m31_months))
        model.m31_fixed_charge_brl = p.Expression(expr=
            len(month_keys) * tariff_policy.monthly_fixed_charge_brl)
        model.m31_bill_before_tax_brl = p.Expression(expr=
            model.m31_energy_cost_brl + model.m31_additional_energy_cost_brl +
            model.m31_demand_cost_brl + model.m31_overrun_cost_brl +
            model.m31_fixed_charge_brl)
        annual_bill_expr = (1 + tariff_policy.tax_fraction_on_bill) * model.m31_bill_before_tax_brl
        model._m31_tariff_policy = tariff_policy
    # For a single representative year, repeat identical costs annually.
    # No load growth, tariff escalation, degradation or re-optimization assumed.
    annuity = sum((1 + cfg.discount_rate_real_year) ** (-y)
                 for y in range(1, cfg.horizon_years + 1))
    fixed_pv = present_value(cfg, pv_kwp, bess_kwh, pcs_kw)
    model.m31_pv_cost_brl = p.Expression(
        expr=fixed_pv["pv_cost_without_variable_bill_brl"]
        + annuity * annual_bill_expr)
    if annual_pkm is not None:
        if annual_pkm <= 0:
            raise ValueError("annual_pkm must be > 0")
        model.m31_f1_brl_per_pkm = p.Expression(
            expr=model.m31_pv_cost_brl / (annual_pkm * annuity))
    model.obj.deactivate()
    model.m31_cost_objective = p.Objective(expr=model.m31_pv_cost_brl, sense=p.minimize)
    return model


def reconcile_economic_dispatch(model, cfg: Economics, *, pv_kwp: float,
                                bess_kwh: float, pcs_kw: float,
                                months: Sequence[int], dt_hours: float,
                                atol_brl: float = 0.01,
                                rtol: float = 1e-8,
                                tariff_policy: TariffPolicy | None = None) -> dict:
    """Audita objetivo M3.1 e fatura ex post a MESMA solução Pyomo.

    Requer MILP resolvido e variáveis carregadas; não resolve nem modifica o modelo.
    A equivalência só vale para tarifa plana de energia e demanda mensal pelo
    máximo observado, sem cobrança contratada, tributos ou encargos extras.
    """
    import math
    import pyomo.environ as p
    from .f1 import annual_bill

    if not hasattr(model, 'm31_cost_objective') or model.m31_cost_objective.active is False:
        raise ValueError('M31_OBJECTIVE_NOT_ACTIVE')
    if model.obj.active:
        raise ValueError('ORIGINAL_OBJECTIVE_STILL_ACTIVE')
    if len(months) != len(model.T):
        raise ValueError('MONTHS_LENGTH_MISMATCH')
    if not math.isfinite(atol_brl) or atol_brl < 0 or not math.isfinite(rtol) or rtol < 0:
        raise ValueError('INVALID_TOLERANCE')
    attached_policy = getattr(model, '_m31_tariff_policy', None)
    if (attached_policy is None) != (tariff_policy is None):
        raise ValueError('TARIFF_POLICY_MISMATCH')
    if attached_policy is not None and attached_policy != tariff_policy:
        raise ValueError('TARIFF_POLICY_MISMATCH')
    grid = []
    for t in model.T:
        value = p.value(model.grid[t], exception=False)
        if value is None or not math.isfinite(float(value)):
            raise ValueError('UNLOADED_GRID_DISPATCH')
        if float(value) < -1e-6:
            raise ValueError('NEGATIVE_GRID_DISPATCH')
        grid.append(max(0.0, float(value)))
    bill = (annual_bill_regulated(cfg, grid, dt_hours, months, tariff_policy)
            if tariff_policy is not None else annual_bill(cfg, grid, dt_hours, months))
    cap = present_value(cfg, pv_kwp, bess_kwh, pcs_kw,
                        annual_variable_bill_brl=bill['total_variable_bill_brl'])
    expr = p.value(model.m31_cost_objective.expr, exception=False)
    if expr is None or not math.isfinite(float(expr)):
        raise ValueError('UNLOADED_ECONOMIC_OBJECTIVE')
    reconstructed = cap['pv_total_cost_brl']
    difference = float(expr) - reconstructed
    tolerance = atol_brl + rtol * max(abs(float(expr)), abs(reconstructed))
    if abs(difference) > tolerance:
        raise ValueError(f'ECONOMIC_RECONCILIATION_FAILED: delta_brl={difference:.9f}')
    monthly_peak_model = {int(m): float(p.value(model.m31_monthly_peak[m]))
                          for m in model.m31_months}
    # Monthly epigraph peaks may be slack when demand tariff is zero.
    if tariff_policy is None and cfg.demand_tariff_brl_per_kw_month > 0:
        for month, peak in bill['monthly_peak_kw'].items():
            if abs(monthly_peak_model[month] - peak) > 1e-5:
                raise ValueError('MONTHLY_PEAK_NOT_TIGHT')
    return {
        'status': ('RECONCILED_EXPLICIT_TARIFF_R0' if tariff_policy is not None
                   else 'RECONCILED_EXPLORATORY_R0'),
        'objective_present_value_brl': float(expr),
        'reconstructed_present_value_brl': reconstructed,
        'difference_brl': difference,
        'energy_kwh': bill['energy_kwh'],
        'energy_cost_brl': bill['energy_cost_brl'],
        'demand_cost_brl': bill['demand_cost_brl'],
        'annual_variable_bill_brl': bill['total_variable_bill_brl'],
        'monthly_peak_kw': bill['monthly_peak_kw'],
        'f2_peak_kw': max(grid),
        'annual_pkm': None,
        'scope': (bill['scope'] if tariff_policy is not None else
                  'flat_energy_tariff_monthly_measured_peak_no_contract_or_extra_charges'),
    }
