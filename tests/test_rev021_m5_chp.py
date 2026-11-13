import pytest
from d28.rev02.operational import Bus, Cabinet, build_operational_milp
from d28.rev02.chp import CHPParameters, attach_chp, solve_chp_operational
from d28.rev02.chp_integration import CHPCase, evaluate_chp_design
from d28.rev02.operational_integration import OperationalCase


def make_model(cap=100, available=(True,True)):
    m=build_operational_milp(buses=[Bus('A',50,100,10,100,(0,0),(True,True),50)],
      cabinets=[Cabinet('C',150,2,('A',))],base_load_kw=(80,80),pv_pu=(0,0),
      dt_hours=1,pcc_cap_kw=cap,tariff_brl_kwh=(1,1))
    p=CHPParameters(.4,.2,.01,available)
    return attach_chp(m,capacity_kw=100,parameters=p,dt_hours=1)


def test_m5_feasible_and_fuel_balance():
    r=solve_chp_operational(make_model())
    assert r['status']=='PASS_SYNTHETIC_OPERATIONAL_CHP'
    assert r['f2_kw'] <= 100+1e-6
    for power,fuel in zip(r['chp_generation_kw'],r['chp_fuel_kwh_lhv']):
        assert fuel == pytest.approx(power/.4)


def test_m5_chp_unavailable():
    r=solve_chp_operational(make_model(available=(False,False)))
    assert r['status']=='PASS_SYNTHETIC_OPERATIONAL_CHP'
    assert r['chp_generation_kw']==pytest.approx([0,0])


def test_m5_fuel_budget_infeasible():
    m=make_model(cap=20)
    # Substituir o parâmetro de disponibilidade não é permitido; limite novo é válido.
    import pyomo.environ as p
    m.extra_fuel_cap=p.Constraint(expr=sum(m.chp_fuel[t] for t in m.T)<=10)
    r=solve_chp_operational(m)
    assert r['status']=='INFEASIBLE_OR_NOT_OPTIMAL'


def test_m5_invalid_efficiency():
    m=build_operational_milp(buses=[Bus('A',50,100,10,100,(0,),(True,),50)],
      cabinets=[Cabinet('C',150,2,('A',))],base_load_kw=(20,),pv_pu=(0,),dt_hours=1,pcc_cap_kw=100)
    with pytest.raises(ValueError,match='eficiência'):
        attach_chp(m,capacity_kw=20,parameters=CHPParameters(0,1,0,(True,)),dt_hours=1)


def test_m5_evaluator_costs():
    c=OperationalCase(buses=(Bus('A',50,100,10,100,(0,0),(True,True),50),),
      cabinets=(Cabinet('C',150,2,('A',)),),base_load_kw=(80,80),
      pv_pu=(0,0),tariff_brl_kwh=(1,1))
    case=CHPCase(c,CHPParameters(.4,.2,.01,(True,True)),1000)
    r=evaluate_chp_design({'chp_kw':100},case)
    assert r['status']=='PASS_SYNTHETIC_M5'
    assert r['costs']['infrastructure_brl']==pytest.approx(100000)
    assert r['f1_brl_per_pkm'] > 0
