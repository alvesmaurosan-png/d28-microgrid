import pytest
from d28.rev02.contracts import Scenario
from d28.rev02.integration import SyntheticCase, annuity_factor, evaluate_design, optimize_synthetic


def test_discount():
    assert annuity_factor(0, 3) == 3
    assert 0 < annuity_factor(.08, 12) < 12
    with pytest.raises(ValueError): annuity_factor(-.1, 3)


def test_c2_refuses_fake_integration():
    with pytest.raises(NotImplementedError, match='Cenario 2'):
        evaluate_design({}, SyntheticCase(scenario=Scenario.C2))


def test_chp_refuses_fake_integration():
    with pytest.raises(NotImplementedError, match='CHP'):
        evaluate_design({'chp_kw':10}, SyntheticCase())


def test_c_rate_blocked_before_solver():
    result = evaluate_design({'bess_kwh':100,'pcs_kw':60},SyntheticCase())
    assert result['status']=='INFEASIBLE_DESIGN'


def test_realista_no_local():
    result = evaluate_design({'pv_kw':10},SyntheticCase(scenario=Scenario.REALISTA))
    assert result['status']=='INFEASIBLE_DESIGN'


def test_synthetic_economics_with_injected_solver():
    pytest.importorskip("pyomo.environ")
    def fake_solve(model):
        assert model._rev02['pcc_kw']==2500
        return {'status':'PASS_ENERGY_ONLY','f2_kw':2100.,'objective_brl':800.}
    result=evaluate_design({'pv_kw':500.,'bess_kwh':1000.,'pcs_kw':200.},SyntheticCase(),solve=fake_solve)
    assert result['status']=='PASS_SYNTHETIC_ENERGY_ONLY'
    assert result['f2_kw']==2100
    assert result['f1_brl_per_pkm']>0
    assert result['costs']['discounted_pkm']>0


def test_real_milp_if_available():
    pytest.importorskip('pyomo.environ')
    import pyomo.environ as p
    if not p.SolverFactory('appsi_highs').available(False):
        pytest.skip('HiGHS nao disponivel')
    case=SyntheticCase(load_kw=(1500.,1600.,1700.,1800.),pv_pu=(0.,.3,.5,0.),tariff_brl_kwh=(.7,)*4,annualization_scale=2190.)
    result=evaluate_design({'pv_kw':1000.,'bess_kwh':1000.,'pcs_kw':300.},case)
    assert result['status']=='PASS_SYNTHETIC_ENERGY_ONLY'
    assert 0 <= result['f2_kw'] <= 2500


def test_nsga2_end_to_end_if_available():
    pytest.importorskip('pyomo.environ')
    import pyomo.environ as p
    if not p.SolverFactory('appsi_highs').available(False):
        pytest.skip('HiGHS nao disponivel')
    result=optimize_synthetic(population=4,generations=1)
    assert result['status']=='PASS_SYNTHETIC_DEMO'
    assert result['nondominated']
    assert all(x['f2_kw']<=2500+1e-6 for x in result['nondominated'])
