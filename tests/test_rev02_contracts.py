import math
import pytest
from d28.rev02.contracts import Scenario, contract, validate_fleet
from d28.rev02.economics import IntegratedCosts
from d28.rev02.nsga2 import dominates, fronts, run
from d28.rev02.readiness import readiness

@pytest.mark.parametrize('s',list(Scenario))
@pytest.mark.parametrize('year,bev',[(2026,100),(2030,300),(2038,450)])
def test_scenario(s,year,bev):
    c=contract(s,year)
    assert c.planned_bev == bev and c.total_fleet == 450
    assert (c.pcc_limit_kw is None) == (s == Scenario.BAU)

def test_fleet():
    validate_fleet(300,150,0)
    with pytest.raises(ValueError):validate_fleet(300,150,10)

def test_integrated_cost():
    c=IntegratedCosts(100,50,10,20,5,5,90)
    assert c.f1_brl_per_pkm()==2
    with pytest.raises(ValueError):IntegratedCosts(1,1,1,1,1,0,0).f1_brl_per_pkm()

def test_nondominated():
    assert fronts([(1,3),(2,2),(3,2)])[0] == [0,1]
    assert dominates((2,2),(3,2))

def test_nsga2():
    result=run(lambda x:(x['x'],1-x['x']),{'x':(0.,1.)},population=8,generations=3)
    assert len(result['population'])==8
    assert all(math.isfinite(z) for pair in result['objectives'] for z in pair)

def test_readiness():
    assert not readiness({})['ready']
