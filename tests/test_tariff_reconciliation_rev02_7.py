"""REV02.7: independent arithmetic and Pyomo reconciliation, synthetic only."""
import pytest
from d28.economics.f1 import Economics, TariffPolicy, annual_bill_regulated, present_value


def cfg():
    return Economics(
        pv_capex_brl_per_kwp=0, bess_capex_brl_per_kwh=0,
        pcs_capex_brl_per_kw=0, engineering_contingency_fraction=0,
        pv_fixed_opex_fraction_of_pv_capex_year=0,
        bess_fixed_opex_fraction_of_bess_capex_year=0,
        pcs_fixed_opex_fraction_of_pcs_capex_year=0,
        energy_tariff_brl_per_kwh=0.75,
        demand_tariff_brl_per_kw_month=30,
        discount_rate_real_year=0,
        horizon_years=2,
        pv_inverter_replacement_year=12,
        pv_inverter_replacement_fraction_of_initial_pv_capex=0,
        bess_replacement_year=12,
        bess_replacement_fraction_of_initial_bess_capex=0,
        pv_capacity_max_kwp=100,
        bess_max_c_rate_per_hour=0.55,
        pcc_import_limit_kw=100,
    )


MONTHS = [202600 + m for m in range(1, 13)]


def policy():
    return TariffPolicy(
        energy_tariffs_brl_per_kwh=tuple([1.0] * 6 + [2.0] * 6),
        contracted_demand_kw_by_month={m: 5.0 for m in MONTHS},
        demand_tariff_brl_per_kw_month=3,
        overrun_threshold_multiplier=1.1,
        overrun_tariff_brl_per_kw_month=4,
        additional_energy_charge_brl_per_kwh=0.5,
        monthly_fixed_charge_brl=2,
        tax_fraction_on_bill=0.1,
    )


def test_manual_bill_and_present_value():
    b = annual_bill_regulated(cfg(), [10.0] * 12, 1.0, MONTHS, policy())
    assert b['energy_kwh'] == 120
    assert b['energy_cost_brl'] == 180
    assert b['additional_energy_charge_brl'] == 60
    assert b['demand_cost_brl'] == 360
    assert b['overrun_cost_brl'] == pytest.approx(216)
    assert b['monthly_fixed_cost_brl'] == 24
    assert b['tax_cost_brl'] == pytest.approx(84)
    assert b['total_variable_bill_brl'] == pytest.approx(924)
    pv = present_value(cfg(), 0, 0, 0, annual_variable_bill_brl=b['total_variable_bill_brl'])
    assert pv['pv_total_cost_brl'] == pytest.approx(1848)


def test_missing_month_blocked():
    with pytest.raises(ValueError, match='TARIFF_CALENDAR'):
        annual_bill_regulated(cfg(), [10.] * 12, 1, MONTHS[:11] + [MONTHS[0]], policy())



def test_short_calendar_blocked_as_length_mismatch():
    with pytest.raises(ValueError, match='TARIFF_SERIES_LENGTH_MISMATCH'):
        annual_bill_regulated(cfg(), [10.] * 11, 1, MONTHS[:11], policy())

def test_missing_tariff_interval_blocked():
    p = policy()
    from dataclasses import replace
    with pytest.raises(ValueError, match='TARIFF_SERIES_LENGTH'):
        annual_bill_regulated(cfg(), [10.] * 12, 1, MONTHS,
                              replace(p, energy_tariffs_brl_per_kwh=(1.,)))


def test_pcc_limit_blocked():
    with pytest.raises(ValueError, match='PCC_LIMIT'):
        annual_bill_regulated(cfg(), [101.] * 12, 1, MONTHS, policy())


def test_pyomo_objective_and_ex_post_reconcile():
    p = pytest.importorskip('pyomo.environ')
    from d28.economics.milp_adapter import attach_economic_objective, reconcile_economic_dispatch
    from d28.dispatch.milp import build_r0_milp
    model = build_r0_milp([10.]*12, [0.]*12, 0, 0, 0,
                          dt_hours=1, pcc_cap_kw=100, terminal_policy='free')
    attach_economic_objective(model, cfg(), pv_kwp=0, bess_kwh=0, pcs_kw=0,
                              months=MONTHS, dt_hours=1, tariff_policy=policy())
    solver = p.SolverFactory('appsi_highs')
    if not solver.available(False):
        pytest.skip('HiGHS unavailable')
    res = solver.solve(model)
    assert str(res.solver.termination_condition).lower() == 'optimal'
    recon = reconcile_economic_dispatch(model, cfg(), pv_kwp=0, bess_kwh=0,
                                        pcs_kw=0, months=MONTHS, dt_hours=1,
                                        tariff_policy=policy())
    assert recon['annual_variable_bill_brl'] == pytest.approx(924)
    assert recon['objective_present_value_brl'] == pytest.approx(1848)
    assert recon['difference_brl'] == pytest.approx(0, abs=1e-5)
    assert recon['f2_peak_kw'] == pytest.approx(10)


def test_tariff_mismatch_blocked():
    p = pytest.importorskip('pyomo.environ')
    from d28.economics.milp_adapter import attach_economic_objective, reconcile_economic_dispatch
    from d28.dispatch.milp import build_r0_milp
    model = build_r0_milp([10.]*12, [0.]*12, 0, 0, 0,
                          dt_hours=1, pcc_cap_kw=100)
    attach_economic_objective(model, cfg(), pv_kwp=0, bess_kwh=0, pcs_kw=0,
                              months=MONTHS, dt_hours=1, tariff_policy=policy())
    with pytest.raises(ValueError, match='TARIFF_POLICY_MISMATCH'):
        reconcile_economic_dispatch(model, cfg(), pv_kwp=0, bess_kwh=0, pcs_kw=0,
                                    months=MONTHS, dt_hours=1)
