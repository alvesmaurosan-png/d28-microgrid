import pytest
from d28.optimization.economic_dispatch_f1f2 import EnergyPrices, _validate, nsga2_objectives_or_infeasible, annual_f1_f2_strict

def test_prices_length():
    with pytest.raises(ValueError): _validate(EnergyPrices((.5,)),4,'R0')
def test_r2_double_count_blocked():
    with pytest.raises(ValueError): _validate(EnergyPrices((.5,)*4,production_brl_nm3=.6,fuel_cost_includes_production=True),4,'R2')
def test_nsga_gate():
    assert not nsga2_objectives_or_infeasible(None)['eligible']
    assert nsga2_objectives_or_infeasible({'objectives':(1.2,100.)})['eligible']
def test_annual_gate():
    with pytest.raises(ValueError,match='ANNUAL_HORIZON_REQUIRED'):
        annual_f1_f2_strict('R0',cfg=None,design={},grid_kw=[1]*4,months=[],dt_hours=.25,annual_pkm=1,accounting=None,contract=None)
