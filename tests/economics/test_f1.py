from datetime import datetime
from pathlib import Path
import pytest
from d28.economics.f1 import Economics, capital_and_fixed_opex, annual_bill, month_groups, present_value
from d28.economics.milp_adapter import attach_economic_objective

CONFIG = Path(__file__).resolve().parents[2] / "config/economics/r0_f1_exploratory_2026.json"
A = (205.4806088017267, 28272.75736597176, 4996.651562474392)
B = (802.2247646664324, 38208.83648964471, 6640.935872558496)
C = (8652.388573894343, 39273.10562110964, 6535.97084299626)


def test_config_and_physical_domain():
    c = Economics.from_json(CONFIG)
    capital_and_fixed_opex(c, *A)
    capital_and_fixed_opex(c, *B)
    with pytest.raises(ValueError, match="roof"):
        capital_and_fixed_opex(c, *C)


def test_capex_components():
    c = Economics.from_json(CONFIG)
    r = capital_and_fixed_opex(c, *A)
    assert r["pv_capex_brl"] == pytest.approx(A[0] * 4000)
    assert r["initial_capex_brl"] == pytest.approx(
        1.1 * (A[0] * 4000 + A[1] * 1500 + A[2] * 900))
    assert r["annual_fixed_opex_brl"] == pytest.approx(
        A[0] * 4000 * 0.015 + A[1] * 1500 * 0.025)


def test_monthly_peaks_not_annual_peak_times_12():
    c = Economics.from_json(CONFIG)
    bill = annual_bill(c, [100, 200, 50, 80], 0.25,
                       [202601, 202601, 202602, 202602])
    assert bill["energy_kwh"] == pytest.approx(107.5)
    assert bill["demand_cost_brl"] == pytest.approx(30 * (200 + 80))


def test_pkm_is_not_invented():
    c = Economics.from_json(CONFIG)
    r = present_value(c, *A)
    assert r["pv_total_cost_brl"] is None
    assert r["f1_brl_per_pkm"] is None
    r = present_value(c, *A, annual_variable_bill_brl=1000, annual_pkm=100000)
    assert r["f1_brl_per_pkm"] > 0


def test_calendar_month_rollover():
    assert month_groups(datetime(2026, 1, 31, 23, 45), 2, 0.25) == [202601, 202602]


def test_opt_in_adapter_no_solve():
    p = pytest.importorskip("pyomo.environ")
    from d28.dispatch.milp import build_r0_milp
    c = Economics.from_json(CONFIG)
    m = build_r0_milp([10] * 12, [0] * 12, 0, 0, 0,
                      dt_hours=0.25, terminal_policy="cyclic")
    attach_economic_objective(m, c, pv_kwp=0, bess_kwh=0, pcs_kw=0,
                              months=[202600 + i for i in range(1, 13)],
                              dt_hours=0.25)
    assert not m.obj.active
    assert m.m31_cost_objective.active
    assert len(m.m31_monthly_peak) == 12
    with pytest.raises(ValueError, match="already attached"):
        attach_economic_objective(m, c, pv_kwp=0, bess_kwh=0, pcs_kw=0,
                                  months=[202600 + i for i in range(1, 13)],
                                  dt_hours=0.25)
