"""REV02.6: manual arithmetic + actual Pyomo/HiGHS R0 reconciliation."""
from dataclasses import replace
import pytest
import pyomo.environ as p
from d28.dispatch.milp import build_r0_milp
from d28.economics.f1 import Economics
from d28.economics.milp_adapter import attach_economic_objective, reconcile_economic_dispatch


def cfg():
    return Economics(
        pv_capex_brl_per_kwp=0, bess_capex_brl_per_kwh=0,
        pcs_capex_brl_per_kw=0, engineering_contingency_fraction=0,
        pv_fixed_opex_fraction_of_pv_capex_year=0,
        bess_fixed_opex_fraction_of_bess_capex_year=0,
        pcs_fixed_opex_fraction_of_pcs_capex_year=0,
        energy_tariff_brl_per_kwh=2,
        demand_tariff_brl_per_kw_month=3,
        discount_rate_real_year=0, horizon_years=2,
        pv_inverter_replacement_year=3,
        pv_inverter_replacement_fraction_of_initial_pv_capex=0,
        bess_replacement_year=3,
        bess_replacement_fraction_of_initial_bess_capex=0,
        pv_capacity_max_kwp=100, bess_max_c_rate_per_hour=0.55,
        pcc_import_limit_kw=100, annual_pkm=None,
    )


def solve_case():
    # Twelve 1h periods, one in each month; exact tariff arithmetic.
    # Grid = 10 kW in each period; energy=120 kWh, energy bill=240 BRL;
    # monthly demand=12*10*3=360 BRL; annual bill=600 BRL;
    # 2-year undiscounted PV=1200 BRL; F2=10 kW.
    loads = [10.] * 12
    months = [202600 + i for i in range(1, 13)]
    m = build_r0_milp(loads, [0.] * 12, 0., 0., 0.,
                      pcc_cap_kw=100, dt_hours=1, terminal_policy='cyclic')
    attach_economic_objective(m, cfg(), pv_kwp=0, bess_kwh=0, pcs_kw=0,
                              months=months, dt_hours=1)
    solver = p.SolverFactory('appsi_highs')
    if not solver.available(False):
        pytest.skip('appsi_highs unavailable')
    result = solver.solve(m)
    assert str(result.solver.termination_condition).lower().endswith('optimal')
    return m, months


def test_manual_reconciliation():
    m, months = solve_case()
    r = reconcile_economic_dispatch(m, cfg(), pv_kwp=0, bess_kwh=0,
                                    pcs_kw=0, months=months, dt_hours=1)
    assert r['energy_kwh'] == pytest.approx(120)
    assert r['energy_cost_brl'] == pytest.approx(240)
    assert r['demand_cost_brl'] == pytest.approx(360)
    assert r['annual_variable_bill_brl'] == pytest.approx(600)
    assert r['objective_present_value_brl'] == pytest.approx(1200)
    assert r['reconstructed_present_value_brl'] == pytest.approx(1200)
    assert r['difference_brl'] == pytest.approx(0, abs=1e-7)
    assert r['f2_peak_kw'] == pytest.approx(10)
    assert r['annual_pkm'] is None


def test_detects_objective_tampering():
    m, months = solve_case()
    m.m31_cost_objective.set_value(m.m31_cost_objective.expr + 100)
    with pytest.raises(ValueError, match='ECONOMIC_RECONCILIATION_FAILED'):
        reconcile_economic_dispatch(m, cfg(), pv_kwp=0, bess_kwh=0,
                                    pcs_kw=0, months=months, dt_hours=1)


def test_rejects_missing_month():
    m, months = solve_case()
    with pytest.raises(ValueError, match='MONTHS_LENGTH_MISMATCH'):
        reconcile_economic_dispatch(m, cfg(), pv_kwp=0, bess_kwh=0,
                                    pcs_kw=0, months=months[:-1], dt_hours=1)
