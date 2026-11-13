import pytest
from d28.rev02.operational import Bus, Cabinet, build_operational_milp, solve_operational_milp


def example(cap=250):
    buses = [Bus('A',50,100,10,100,(0,30,0),(True,False,True),50),
             Bus('B',40,100,10,100,(0,20,0),(True,False,True),40)]
    cabinets = [Cabinet('dual150',150,2,('A','B'))]
    return build_operational_milp(buses=buses,cabinets=cabinets,
        base_load_kw=[20,20,20],pv_pu=[0,0,0],dt_hours=1,
        pcc_cap_kw=cap,tariff_brl_kwh=[1,1,1])


def test_feasible_shared_cabinet():
    r=solve_operational_milp(example())
    assert r['status']=='PASS_SYNTHETIC_OPERATIONAL'
    assert r['f2_kw'] <= 250
    assert r['charging_kw']['A'][1] == pytest.approx(0)
    assert r['charging_kw']['B'][1] == pytest.approx(0)
    assert all(r['charging_kw'][b][t] <= 100+1e-6 for b in ('A','B') for t in range(3))
    assert all(sum(r['charging_kw'][b][t] for b in ('A','B')) <= 150+1e-6 for t in range(3))


def test_infeasible_power_is_reported():
    r=solve_operational_milp(example(cap=20))
    assert r['status']=='INFEASIBLE_OR_NOT_OPTIMAL'


def test_no_double_count_and_missing_eligibility():
    with pytest.raises(ValueError,match='sem gabinete'):
        build_operational_milp(buses=[Bus('A',50,100,10,100,(0,),(True,),50)],
          cabinets=[Cabinet('X',150,2,())],base_load_kw=[0],pv_pu=[0],dt_hours=1,pcc_cap_kw=250)


def test_duplicate_bus_ids():
    b=Bus('A',50,100,10,100,(0,),(True,),50)
    with pytest.raises(ValueError,match='duplicados'):
        build_operational_milp(buses=[b,b],cabinets=[Cabinet('X',150,2,('A',))],
          base_load_kw=[0],pv_pu=[0],dt_hours=1,pcc_cap_kw=250)
