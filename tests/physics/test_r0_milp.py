"""Testes físicos sintéticos R0; não homologam as entradas D28."""
import pytest

p = pytest.importorskip("pyomo.environ")
from d28.dispatch.milp import build_r0_milp, build_r0_smoke


def solve(model):
    solver = p.SolverFactory("appsi_highs")
    if not solver.available():
        pytest.skip("HiGHS indisponível")
    result = solver.solve(model, load_solutions=False)
    assert result.solver.termination_condition == p.TerminationCondition.optimal
    model.solutions.load_from(result)
    return model


def test_legacy_smoke_preserved():
    model = build_r0_smoke([100., 150.], [0., 0.5], 100.)
    solve(model)
    assert p.value(model.grid[0]) == pytest.approx(100)
    assert p.value(model.grid[1]) == pytest.approx(100)


def test_r0_balance_pv_curtailment_and_pcc():
    model = solve(build_r0_milp([10., 50., 20.], [0., 1., 0.5], 100., 0., 0.))
    for t in model.T:
        assert p.value(model.grid[t] + model.pv[t] + model.bess_discharge[t]
                       - model.load_kw[t] - model.bess_charge[t]) == pytest.approx(0, abs=1e-7)
        assert p.value(model.pv[t] + model.pv_curt[t]) == pytest.approx(
            100 * p.value(model.pv_pu[t]), abs=1e-7
        )
        assert 0 <= p.value(model.grid[t]) <= 2500
    assert p.value(model.pv_curt[1]) == pytest.approx(50, abs=1e-7)
    assert p.value(model.obj) == pytest.approx(2.5, abs=1e-7)


def test_bess_physics_and_cyclic_terminal():
    model = solve(build_r0_milp(
        [80., 160., 80., 160.], [0., 0., 0., 0.], 0.,
        200., 100., terminal_policy="cyclic", pcc_cap_kw=2500.
    ))
    assert p.value(model.bess_energy[0]) == pytest.approx(100)
    assert p.value(model.bess_energy[4]) == pytest.approx(100)
    for t in model.T:
        charge = p.value(model.bess_charge[t])
        discharge = p.value(model.bess_discharge[t])
        mode = p.value(model.bess_mode[t])
        assert charge <= 100 * mode + 1e-7
        assert discharge <= 100 * (1 - mode) + 1e-7
        assert charge * discharge == pytest.approx(0, abs=1e-7)
        assert p.value(model.bess_energy[t + 1]) == pytest.approx(
            p.value(model.bess_energy[t]) + 0.922 * charge * 0.25
            - discharge * 0.25 / 0.922, abs=1e-7
        )
    for s in model.S:
        assert 20 - 1e-7 <= p.value(model.bess_energy[s]) <= 180 + 1e-7


def test_soh_limits_and_terminal_fixed():
    model = solve(build_r0_milp(
        [0.], [0.], 0., 100., 50., soh=0.8,
        terminal_policy="fixed", terminal_energy_kwh=40.
    ))
    assert p.value(model.bess_energy[0]) == pytest.approx(40)
    assert p.value(model.bess_energy[1]) == pytest.approx(40)
    assert model.bess_energy[1].ub == pytest.approx(72)
    assert model.bess_energy[1].lb == pytest.approx(8)


def test_pcc_infeasible_without_slack():
    model = build_r0_milp([2600.], [0.], 0., 0., 0.)
    solver = p.SolverFactory("appsi_highs")
    if not solver.available():
        pytest.skip("HiGHS indisponível")
    # O solver pode lançar exceção ao tentar carregar solução inviável.
    result = solver.solve(model, load_solutions=False)
    assert result.solver.termination_condition == p.TerminationCondition.infeasible


@pytest.mark.parametrize("kwargs", [
    {"pcs_power_kw": 60.},
    {"soh": 0.},
    {"terminal_policy": "unknown"},
    {"terminal_policy": "fixed"},
    {"pv_capacity_max_kwp": 10.},
])
def test_invalid_parameters(kwargs):
    params = dict(load_kw=[10.], pv_pu=[0.], pv_capacity_kw=20.,
                  bess_capacity_kwh=100., pcs_power_kw=50.)
    params.update(kwargs)
    with pytest.raises(ValueError):
        build_r0_milp(**params)
