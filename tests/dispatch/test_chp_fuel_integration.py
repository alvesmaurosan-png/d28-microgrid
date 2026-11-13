"""M3.5-B — Integração econômica pós-solução do R1."""

import pytest
import pyomo.environ as p

from d28.dispatch.r1 import build_r1_milp
from d28.dispatch.milp import build_r0_milp
from d28.economics.chp_fuel import natural_gas_cost_from_solved_model


def common_inputs():
    return dict(
        load_kw=[100] * 4,
        pv_pu=[0] * 4,
        pv_capacity_kw=0,
        bess_capacity_kwh=0,
        pcs_power_kw=0,
        dt_hours=0.25,
    )


def build_fixed_chp_r1():
    model = build_r1_milp(
        **common_inputs(),
        chp_capacity_kw=100,
        electrical_efficiency=0.35,
        fuel_lhv_kwh_per_nm3=9.5,
        availability=[1] * 4,
    )

    for t in model.T:
        model.chp.power_gross_kw[t].fix(75)

    return model


def solve_optimal(model):
    solver = p.SolverFactory("appsi_highs")
    assert solver.available()

    result = solver.solve(model)

    assert (
        result.solver.termination_condition
        == p.TerminationCondition.optimal
    )

    return result


def test_r1_fuel_cost_from_optimal_solution():
    model = build_fixed_chp_r1()
    result = solve_optimal(model)

    expected_volume = 75.0 / (0.35 * 9.5)
    expected_cost = expected_volume * 3.0

    actual_volume = sum(
        p.value(model.chp.fuel_nm3[t])
        for t in model.T
    )

    actual_cost = natural_gas_cost_from_solved_model(
        model,
        3.0,
        solver_result=result,
    )

    assert actual_volume == pytest.approx(
        expected_volume, abs=1e-6
    )
    assert actual_cost == pytest.approx(
        expected_cost, abs=1e-6
    )

    assert sum(
        p.value(model.grid[t]) * 0.25
        for t in model.T
    ) == pytest.approx(25.0, abs=1e-6)


def test_reject_missing_solver_result():
    model = build_fixed_chp_r1()

    with pytest.raises(ValueError):
        natural_gas_cost_from_solved_model(
            model, 3.0, solver_result=None
        )


def test_reject_nonoptimal_solver_result():
    model = build_fixed_chp_r1()
    result = solve_optimal(model)

    result.solver.termination_condition = (
        p.TerminationCondition.infeasible
    )

    with pytest.raises(ValueError):
        natural_gas_cost_from_solved_model(
            model, 3.0, solver_result=result
        )


def test_reject_r0_architecture():
    model = build_r0_milp(**common_inputs())
    result = solve_optimal(model)

    with pytest.raises(ValueError):
        natural_gas_cost_from_solved_model(
            model, 3.0, solver_result=result
        )


def test_reject_undefined_fuel_variable():
    model = build_fixed_chp_r1()
    result = solve_optimal(model)

    model.chp.fuel_nm3[0].set_value(None)

    with pytest.raises(ValueError):
        natural_gas_cost_from_solved_model(
            model, 3.0, solver_result=result
        )
