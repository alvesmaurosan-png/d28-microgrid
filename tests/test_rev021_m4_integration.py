import pytest
from d28.rev02.operational import Bus, Cabinet
from d28.rev02.operational_integration import (
    OperationalCase, evaluate_operational_design, optimize_operational_synthetic)


def case():
    return OperationalCase(
        buses=(Bus('A', 50, 100, 10, 100, (0, 30, 0),
                   (True, False, True), 50),),
        cabinets=(Cabinet('dual150', 150, 2, ('A',)),),
        base_load_kw=(20, 20, 20), pv_pu=(0, 0, 0),
        tariff_brl_kwh=(1, 1, 1))


def test_m4_c_rate():
    r = evaluate_operational_design({'bess_kwh':100,'pcs_kw':60},case())
    assert r['status'] == 'INFEASIBLE_DESIGN'


def test_m4_no_chp():
    with pytest.raises(NotImplementedError):
        evaluate_operational_design({'chp_kw':1},case())


def test_m4_objectives_and_trace_with_injected_solver():
    def solve(m):
        assert m._rev021['bus_count'] == 1
        return {'status':'PASS_SYNTHETIC_OPERATIONAL','f2_kw':30.,
                'objective_brl':90.,'charging_kw':{'A':[0,0,0]}}
    r = evaluate_operational_design({'pv_kw':10,'bess_kwh':100,'pcs_kw':20},
                                    case(),solve=solve)
    assert r['status'] == 'PASS_SYNTHETIC_OPERATIONAL_INTEGRATION'
    assert r['f2_kw'] == 30
    assert r['f1_brl_per_pkm'] > 0
    assert 'operational' in r


def test_m4_infeasibility_propagates():
    r = evaluate_operational_design({},case(),
        solve=lambda m: {'status':'INFEASIBLE_OR_NOT_OPTIMAL','termination':'infeasible'})
    assert r['status'] == 'INFEASIBLE_MILP'
    assert r['reason'] == 'infeasible'


def test_m4_nsga2_real_solver_if_available():
    p = pytest.importorskip('pyomo.environ')
    if not p.SolverFactory('appsi_highs').available(False):
        pytest.skip('HiGHS indisponivel')
    r = optimize_operational_synthetic(case(),population=4,generations=1)
    assert r['status'] == 'PASS_SYNTHETIC_M4'
    assert r['nondominated']
    assert all(x['f2_kw'] <= 2500 for x in r['nondominated'])
