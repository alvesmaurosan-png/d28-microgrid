
import pytest

from d28.dispatch.milp import build_r0_milp
from d28.economics.f1 import Economics
from d28.objectives.r0_evaluator import evaluate_r0_model


@pytest.fixture
def case():
    cfg = Economics.from_json(
        "config/economics/r0_f1_exploratory_2026.json"
    )

    model = build_r0_milp(
        load_kw=[100.0] * 4,
        pv_pu=[0.0, 0.1, 0.0, 0.0],
        pv_capacity_kw=100.0,
        bess_capacity_kwh=1000.0,
        pcs_power_kw=200.0,
        pcc_cap_kw=cfg.pcc_import_limit_kw,
        dt_hours=0.25,
        initial_soc=0.5,
        terminal_policy="cyclic",
    )

    for t in model.T:
        model.grid[t].set_value(100.0)
        model.pv[t].set_value(0.0)
        model.pv_curt[t].set_value(10.0 if t == 1 else 0.0)
        model.bess_charge[t].set_value(0.0)
        model.bess_discharge[t].set_value(0.0)
        model.bess_mode[t].set_value(0)

    for s in model.S:
        model.bess_energy[s].set_value(500.0)

    kwargs = dict(
        load_kw=[100.0] * 4,
        pv_pu=[0.0, 0.1, 0.0, 0.0],
        pv_kwp=100.0,
        bess_kwh=1000.0,
        pcs_kw=200.0,
        months=[202501] * 4,
        dt_hours=0.25,
    )

    return model, cfg, kwargs


def test_feasible_dispatch(case):
    model, cfg, kwargs = case
    result = evaluate_r0_model(model, cfg, **kwargs)

    assert result["status"] == "FEASIBLE_DISPATCH_EVALUATED"
    assert result["physical"]["passed"]
    assert result["photovoltaic"]["passed"]
    assert result["pyomo_audit"]["passed"]
    assert result["objectives_evaluated"]
    assert result["objectives"]["f2_peak_kw"] == pytest.approx(100.0)
    assert result["objectives"]["f3"] is None
    assert result["solver_optimality_certified"] is False


def test_initial_soc_violation_blocks_objectives(case):
    model, cfg, kwargs = case
    model.bess_energy[0].set_value(550.0)

    result = evaluate_r0_model(model, cfg, **kwargs)

    assert result["status"] == "INFEASIBLE_DISPATCH_VALUES"
    assert not result["pyomo_audit"]["passed"]
    assert result["pyomo_audit"]["residuals"]["bess_initial"] == pytest.approx(50.0)
    assert not result["objectives_evaluated"]
    assert "objectives" not in result


def test_pv_balance_violation_blocks_objectives(case):
    model, cfg, kwargs = case
    model.pv_curt[1].set_value(5.0)

    result = evaluate_r0_model(model, cfg, **kwargs)

    assert result["status"] == "INFEASIBLE_DISPATCH_VALUES"
    assert not result["photovoltaic"]["passed"]
    assert not result["objectives_evaluated"]


def test_binary_integrality_violation_blocks_objectives(case):
    model, cfg, kwargs = case
    model.bess_mode[0].set_value(0.5, skip_validation=True)

    result = evaluate_r0_model(model, cfg, **kwargs)

    assert result["status"] == "INFEASIBLE_DISPATCH_VALUES"
    assert not result["pyomo_audit"]["passed"]
    assert result["pyomo_audit"]["residuals"]["variable_domains"] > 0
    assert not result["objectives_evaluated"]
