"""M3.2 — Testes de integração elétrica R1."""

import pytest
import pyomo.environ as p

from d28.dispatch.r1 import build_r1_milp


def test_r1_integrated_electric_balance():
    """Verifica conservação elétrica com CHP integrado ao R1."""

    m = build_r1_milp(
        load_kw=[100, 150, 120, 80],
        pv_pu=[0, 0.3, 0.5, 0.1],
        pv_capacity_kw=100,
        bess_capacity_kwh=200,
        pcs_power_kw=100,
        chp_capacity_kw=100,
        electrical_efficiency=0.35,
        fuel_lhv_kwh_per_nm3=9.5,
        availability=[1, 1, 0, 1],
        dt_hours=0.25,
    )

    for t in m.T:
        m.chp.power_gross_kw[t].fix(75 if t == 0 else 0)

    solver = p.SolverFactory("appsi_highs")
    assert solver.available()

    result = solver.solve(m)

    assert result.solver.termination_condition == p.TerminationCondition.optimal

    for t in m.T:
        supply = (
            p.value(m.grid[t])
            + p.value(m.pv[t])
            + p.value(m.bess_discharge[t])
            + p.value(m.chp.power_gross_kw[t])
        )

        demand = (
            p.value(m.load_kw[t])
            + p.value(m.bess_charge[t])
        )

        assert abs(supply - demand) <= 1e-6

        expected_chp = 75 if t == 0 else 0
        assert p.value(m.chp.power_gross_kw[t]) == pytest.approx(
            expected_chp, abs=1e-6
        )

        assert p.value(m.chp.on[t]) <= p.value(m.chp.available[t]) + 1e-6

    assert m._r0_metadata["architecture"] == "R1"
    assert m._r0_metadata["scientific_validation"] is False


def test_r1_chp_displaces_grid_import_against_r0():
    """Compara R0 e R1 sem PV/BESS, com CHP fixado em 75 kW."""

    from d28.dispatch.milp import build_r0_milp

    common = dict(
        load_kw=[100] * 4,
        pv_pu=[0] * 4,
        pv_capacity_kw=0,
        bess_capacity_kwh=0,
        pcs_power_kw=0,
        dt_hours=0.25,
    )

    r0 = build_r0_milp(**common)

    r1 = build_r1_milp(
        **common,
        chp_capacity_kw=100,
        electrical_efficiency=0.35,
        fuel_lhv_kwh_per_nm3=9.5,
        availability=[1] * 4,
    )

    for t in r1.T:
        r1.chp.power_gross_kw[t].fix(75)

    solver = p.SolverFactory("appsi_highs")

    for model in (r0, r1):
        result = solver.solve(model)
        assert (
            result.solver.termination_condition
            == p.TerminationCondition.optimal
        )

    for t in r0.T:
        assert p.value(r0.grid[t]) == pytest.approx(100, abs=1e-6)
        assert p.value(r1.grid[t]) == pytest.approx(25, abs=1e-6)

    energy_r0 = sum(p.value(r0.grid[t]) for t in r0.T) * 0.25
    energy_r1 = sum(p.value(r1.grid[t]) for t in r1.T) * 0.25

    assert energy_r0 == pytest.approx(100, abs=1e-6)
    assert energy_r1 == pytest.approx(25, abs=1e-6)
    assert energy_r0 - energy_r1 == pytest.approx(75, abs=1e-6)


def test_r1_autonomous_chp_dispatch():
    """Verifica acionamento, minimo tecnico e indisponibilidade do CHP."""

    m = build_r1_milp(
        load_kw=[40, 80, 120, 30],
        pv_pu=[0, 0, 0, 0],
        pv_capacity_kw=0,
        bess_capacity_kwh=0,
        pcs_power_kw=0,
        chp_capacity_kw=100,
        electrical_efficiency=0.35,
        fuel_lhv_kwh_per_nm3=9.5,
        availability=[1, 1, 0, 1],
        dt_hours=0.25,
    )

    solver = p.SolverFactory("appsi_highs")
    result = solver.solve(m)

    assert (
        result.solver.termination_condition
        == p.TerminationCondition.optimal
    )

    expected_on = [0, 1, 0, 0]
    expected_chp = [0, 80, 0, 0]
    expected_grid = [40, 0, 120, 30]

    for t in m.T:
        assert p.value(m.chp.on[t]) == pytest.approx(
            expected_on[t], abs=1e-6
        )
        assert p.value(m.chp.power_gross_kw[t]) == pytest.approx(
            expected_chp[t], abs=1e-6
        )
        assert p.value(m.grid[t]) == pytest.approx(
            expected_grid[t], abs=1e-6
        )

    expected_fuel = 80 * 0.25 / (0.35 * 9.5)

    assert p.value(m.chp.fuel_nm3[1]) == pytest.approx(
        expected_fuel, abs=1e-6
    )
