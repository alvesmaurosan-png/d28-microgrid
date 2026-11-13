"""M2-R0-AUD01: testes físicos adicionais, exclusivamente sintéticos.

Não altera build_r0_milp, entradas D28, manifestos ou histórico Git.
Executar: python -m pytest tests/physics/test_r0_aud01.py -v
"""

import math

import pytest

p = pytest.importorskip("pyomo.environ")
from d28.dispatch.milp import build_r0_milp

DT = 0.25
ETA = 0.922
TOL = 1e-6


def _solve(model, *, feasible=True):
    solver = p.SolverFactory("appsi_highs")
    if not solver.available():
        pytest.skip("HiGHS indisponível")
    result = solver.solve(model, load_solutions=False)
    termination = result.solver.termination_condition
    if feasible:
        assert termination == p.TerminationCondition.optimal
        model.solutions.load_from(result)
        return model
    assert termination == p.TerminationCondition.infeasible
    return result


def _v(expr):
    return p.value(expr)


def _base(**overrides):
    params = dict(load_kw=[10.], pv_pu=[0.], pv_capacity_kw=0.,
                  bess_capacity_kwh=100., pcs_power_kw=50.)
    params.update(overrides)
    return build_r0_milp(**params)


def _assert_physics(model, *, pcs_kw, capacity_kwh, soh=1., dt=DT,
                    eta_ch=ETA, eta_dis=ETA, pcc_kw=2500.):
    """Balanços calculados a partir de variáveis, sem avaliar constraints Pyomo."""
    low = 0.10 * capacity_kwh * soh
    high = 0.90 * capacity_kwh * soh
    for s in model.S:
        assert low - TOL <= _v(model.bess_energy[s]) <= high + TOL
    for t in model.T:
        grid = _v(model.grid[t])
        pv = _v(model.pv[t])
        curtailed = _v(model.pv_curt[t])
        charge = _v(model.bess_charge[t])
        discharge = _v(model.bess_discharge[t])
        mode = _v(model.bess_mode[t])
        e0, e1 = _v(model.bess_energy[t]), _v(model.bess_energy[t + 1])
        load = _v(model.load_kw[t])
        available_pv = _v(model.pv_pu[t]) * model._aud01_pv_kw
        assert grid + pv + discharge == pytest.approx(load + charge, abs=TOL)
        assert pv + curtailed == pytest.approx(available_pv, abs=TOL)
        assert e1 == pytest.approx(e0 + eta_ch * charge * dt
                                   - discharge * dt / eta_dis, abs=TOL)
        assert -TOL <= grid <= pcc_kw + TOL
        assert pv >= -TOL and curtailed >= -TOL
        assert charge >= -TOL and discharge >= -TOL
        assert charge <= pcs_kw * mode + TOL
        assert discharge <= pcs_kw * (1 - mode) + TOL
        assert charge * discharge == pytest.approx(0., abs=TOL)


def _tag_pv(model, capacity_kw):
    model._aud01_pv_kw = capacity_kw
    return model


# AUD01-01: carga forçada por energia terminal, sem geração FV.
def test_aud01_01_effective_charge_independent_energy():
    model = _solve(_base(load_kw=[0.], terminal_policy="fixed",
                         terminal_energy_kwh=60.))
    charge_expected = (60. - 50.) / (ETA * DT)
    assert _v(model.bess_charge[0]) == pytest.approx(charge_expected, abs=TOL)
    assert _v(model.bess_discharge[0]) == pytest.approx(0., abs=TOL)
    assert _v(model.grid[0]) == pytest.approx(charge_expected, abs=TOL)
    assert _v(model.bess_energy[1]) == pytest.approx(60., abs=TOL)
    assert _v(model.obj) == pytest.approx(charge_expected * DT, abs=TOL)
    _assert_physics(_tag_pv(model, 0.), pcs_kw=50., capacity_kwh=100.)


# AUD01-02: descarga forçada pelo PCC e limitada pelo PCS.
def test_aud01_02_effective_discharge_independent_energy():
    model = _solve(_base(load_kw=[60.], pcc_cap_kw=20., pcs_power_kw=40.))
    assert _v(model.bess_discharge[0]) == pytest.approx(40., abs=TOL)
    assert _v(model.bess_charge[0]) == pytest.approx(0., abs=TOL)
    assert _v(model.grid[0]) == pytest.approx(20., abs=TOL)
    assert _v(model.bess_energy[1]) == pytest.approx(
        50. - 40. * DT / ETA, abs=TOL)
    _assert_physics(_tag_pv(model, 0.), pcs_kw=40., capacity_kwh=100., pcc_kw=20.)


# AUD01-03: potência insuficiente, embora haja energia armazenada.
def test_aud01_03_infeasible_pcs_power():
    _solve(_base(load_kw=[60.], pcc_cap_kw=20., pcs_power_kw=30.), feasible=False)


# AUD01-04: PCS adequado em cada intervalo, mas energia total insuficiente.
def test_aud01_04_infeasible_bess_energy():
    _solve(_base(load_kw=[45.] * 4, pv_pu=[0.] * 4, pcc_cap_kw=0., pcs_power_kw=50.), feasible=False)
    # Necessidade: 45 kW x 1 h / 0,922 = 48,81 kWh; disponível: 50 - 10 = 40 kWh.
    assert 45. * 4 * DT / ETA > 50. - 10.


# AUD01-05: alvo terminal dentro da faixa SOC, mas inacessível fisicamente.
def test_aud01_05_infeasible_terminal_target():
    _solve(_base(load_kw=[0.], pcc_cap_kw=0., terminal_policy="fixed",
                 terminal_energy_kwh=60.), feasible=False)


# AUD01-06: ciclo com carga FV no primeiro intervalo e descarga no segundo.
def test_aud01_06_cyclic_with_active_charge_and_discharge():
    model = _solve(_base(load_kw=[0., 20.], pv_pu=[1., 0.],
                         pv_capacity_kw=100., pcc_cap_kw=0.,
                         terminal_policy="cyclic"))
    assert _v(model.bess_energy[0]) == pytest.approx(50., abs=TOL)
    assert _v(model.bess_energy[2]) == pytest.approx(50., abs=TOL)
    charge_expected = 20. / (ETA * ETA)
    assert _v(model.bess_charge[0]) == pytest.approx(charge_expected, abs=TOL)
    assert _v(model.bess_discharge[1]) == pytest.approx(20., abs=TOL)
    assert _v(model.bess_charge[1]) == pytest.approx(0., abs=TOL)
    assert _v(model.bess_discharge[0]) == pytest.approx(0., abs=TOL)
    assert _v(model.pv[0]) == pytest.approx(charge_expected, abs=TOL)
    assert _v(model.pv_curt[0]) == pytest.approx(100. - charge_expected, abs=TOL)
    _assert_physics(_tag_pv(model, 100.), pcs_kw=50., capacity_kwh=100., pcc_kw=0.)


# AUD01-07: PV nulo, excesso de PV, corte total e demanda maior que geração.
@pytest.mark.parametrize("load,pu,capacity,expected_pv,expected_curt,expected_grid", [
    (0., 0., 100., 0., 0., 0.),
    (0., 1., 100., 0., 100., 0.),
    (40., 1., 100., 40., 60., 0.),
    (150., 1., 100., 100., 0., 50.),
    (30., 0., 100., 0., 0., 30.),
])
def test_aud01_07_pv_extremes(load, pu, capacity, expected_pv,
                                expected_curt, expected_grid):
    model = _solve(_base(load_kw=[load], pv_pu=[pu], pv_capacity_kw=capacity,
                         bess_capacity_kwh=0., pcs_power_kw=0.))
    assert _v(model.pv[0]) == pytest.approx(expected_pv, abs=TOL)
    assert _v(model.pv_curt[0]) == pytest.approx(expected_curt, abs=TOL)
    assert _v(model.grid[0]) == pytest.approx(expected_grid, abs=TOL)
    _assert_physics(_tag_pv(model, capacity), pcs_kw=0., capacity_kwh=0.)


# AUD01-08: entradas numéricas e políticas inválidas rejeitadas antes do solve.
@pytest.mark.parametrize("changes", [
    {"load_kw": []},
    {"load_kw": [1., 2.]},
    {"load_kw": [-1.]},
    {"load_kw": [float("nan")]},
    {"load_kw": [float("inf")]},
    {"pv_pu": [-0.1]},
    {"pv_pu": [float("nan")]},
    {"pv_capacity_kw": -1.},
    {"bess_capacity_kwh": -1.},
    {"pcs_power_kw": -1.},
    {"pcc_cap_kw": -1.},
    {"dt_hours": 0.},
    {"dt_hours": -0.25},
    {"eta_charge": 0.},
    {"eta_charge": 1.01},
    {"eta_discharge": 0.},
    {"eta_discharge": 1.01},
    {"soh": -0.1},
    {"soh": 1.01},
    {"initial_soc": 0.09},
    {"initial_soc": 0.91},
    {"pv_capacity_max_kwp": -1.},
    {"pv_capacity_kw": 20., "pv_capacity_max_kwp": 10.},
    {"terminal_policy": "invalid"},
    {"terminal_policy": "fixed"},
    {"terminal_policy": "free", "terminal_energy_kwh": 50.},
    {"terminal_policy": "fixed", "terminal_energy_kwh": 95.},
    {"terminal_policy": "fixed", "terminal_energy_kwh": float("nan")},
    {"pcs_power_kw": 55.1},
])
def test_aud01_08_invalid_parameters(changes):
    with pytest.raises(ValueError):
        _base(**changes)


def test_aud01_08_zero_capacity_requires_zero_pcs():
    model = _solve(_base(load_kw=[0.], bess_capacity_kwh=0., pcs_power_kw=0.))
    assert _v(model.bess_energy[0]) == pytest.approx(0., abs=TOL)
    assert _v(model.bess_energy[1]) == pytest.approx(0., abs=TOL)
    assert _v(model.bess_charge[0]) == pytest.approx(0., abs=TOL)
    assert _v(model.bess_discharge[0]) == pytest.approx(0., abs=TOL)
