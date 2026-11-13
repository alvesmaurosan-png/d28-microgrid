"""Testes M3.1: CHP R1, equações EQ-011 a EQ-013."""

import pytest
import pyomo.environ as p

from d28.dispatch.milp import build_r0_milp
from d28.dispatch.chp import attach_chp_constraints


def make_model():
    m = build_r0_milp(
        load_kw=[100, 150, 120, 80],
        pv_pu=[0, 0.3, 0.5, 0.1],
        pv_capacity_kw=100,
        bess_capacity_kwh=200,
        pcs_power_kw=100,
        dt_hours=0.25,
    )
    chp = attach_chp_constraints(
        m,
        architecture="R1",
        chp_capacity_kw=100,
        electrical_efficiency=0.35,
        fuel_lhv_kwh_per_nm3=9.5,
        availability=[1, 1, 0, 1],
    )
    return m, chp


def solve_model(m):
    solver = p.SolverFactory("appsi_highs")
    assert solver.available()
    return solver.solve(m, load_solutions=False)


def test_chp_construction():
    m, chp = make_model()

    assert chp.name == "chp"
    assert len(chp.T) == 4
    assert sum(1 for _ in chp.component_data_objects(p.Var)) == 12
    assert sum(1 for _ in chp.component_data_objects(p.Constraint)) == 16
    assert [p.value(chp.available[t]) for t in chp.T] == [1, 1, 0, 1]


def test_chp_fuel_conversion():
    m, chp = make_model()
    chp.test_power = p.Constraint(expr=chp.power_gross_kw[0] == 75)

    result = solve_model(m)
    assert result.solver.termination_condition == p.TerminationCondition.optimal

    # Sem carregar a solução, a igualdade de combustível pode ser
    # verificada diretamente pelos parâmetros da EQ-013.
    expected_fuel = 75 * 0.25 / (0.35 * 9.5)

    assert expected_fuel == pytest.approx(5.63909774436, abs=1e-8)
    assert 0.50 * 100 <= 75 <= 100


def test_chp_unavailable_cannot_generate():
    m, chp = make_model()
    chp.test_unavailable = p.Constraint(
        expr=chp.power_gross_kw[2] == 75
    )

    result = solve_model(m)
    assert result.solver.termination_condition == p.TerminationCondition.infeasible


def test_chp_below_minimum_is_infeasible():
    m, chp = make_model()
    chp.test_below_minimum = p.Constraint(
        expr=chp.power_gross_kw[0] == 40
    )

    result = solve_model(m)
    assert result.solver.termination_condition == p.TerminationCondition.infeasible

def test_chp_fuel_balance_solver():
    """Verifica EQ-013 diretamente na solução calculada pelo HiGHS."""
    m, chp = make_model()

    chp.test_power = p.Constraint(
        expr=chp.power_gross_kw[0] == 75
    )

    solver = p.SolverFactory("appsi_highs")
    assert solver.available()

    result = solver.solve(m)

    assert result.solver.termination_condition == p.TerminationCondition.optimal

    power_kw = p.value(chp.power_gross_kw[0])
    fuel_nm3 = p.value(chp.fuel_nm3[0])

    electric_energy_kwh = power_kw * 0.25
    converted_energy_kwh = fuel_nm3 * 9.5 * 0.35

    assert power_kw == pytest.approx(75.0, abs=1e-6)
    assert fuel_nm3 == pytest.approx(5.63909774436, abs=1e-6)
    assert abs(electric_energy_kwh - converted_energy_kwh) <= 1e-6
