import pytest
from d28.optimization.synthetic_chain_r0_r3 import SyntheticInputs, evaluate_synthetic

BASE = dict(pkm_horizon=1000,grid_brl_per_kwh=1,grid_kgco2e_per_kwh=.1,
            fuel_brl_per_nm3=2,fuel_kgco2e_per_nm3=.2,
            equipment_cost_brl_horizon=10,equipment_kgco2e_horizon=1)

def test_reject_zero_pkm():
    with pytest.raises(ValueError,match='PKM'):
        evaluate_synthetic('R0',common={},inputs=SyntheticInputs(**{**BASE,'pkm_horizon':0}))

def test_reject_cgob_credit():
    with pytest.raises(ValueError,match='CGOB'):
        evaluate_synthetic('R3',common={},inputs=SyntheticInputs(**{**BASE,'cgob_kgco2e_credit_horizon':1}))

def test_reject_nan():
    with pytest.raises(ValueError,match='inválida'):
        evaluate_synthetic('R0',common={},inputs=SyntheticInputs(**{**BASE,'grid_brl_per_kwh':float('nan')}))

def test_full_chain_four_routes():
    pytest.importorskip('pyomo.environ')
    import pyomo.environ as p
    if not p.SolverFactory('appsi_highs').available(exception_flag=False):
        pytest.skip('HiGHS indisponível')
    from scripts.validar_cadeia_sintetica_r0_r3 import COMMON,CHP
    for route in ('R0','R1','R2','R3'):
        kw={'common':COMMON,'inputs':SyntheticInputs(**BASE)}
        if route!='R0':kw['chp']=CHP
        if route=='R2':kw['biogas']=dict(production_nm3=[5.]*4,gasometer_capacity_nm3=50.,initial_gas_nm3=20.)
        if route=='R3':kw['cgob']=dict(cgob_coverage_nm3=1.)
        result=evaluate_synthetic(route,**kw)
        assert result['scope']=='SYNTHETIC_HORIZON_NOT_ANNUAL'
        assert not result['scientific_objectives_validated']
        assert not result['nsga2_released']
        assert all(x>=0 for x in result['objectives'].values())
        assert result['audit']['grid_kwh']>=0
