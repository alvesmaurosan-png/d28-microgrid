import pytest
from d28.rev02.dispatch import build_energy_milp

def test_bau_requires_explicit_grid_cap():
    with pytest.raises(ValueError,match='BAU exige'):
        build_energy_milp(scenario='BAU',year=2026,load_kw=[1],pv_pu=[0],dt_hours=.25)

def test_realista_no_local_generation():
    with pytest.raises(ValueError,match='Realista'):
        build_energy_milp(scenario='Realista',year=2026,load_kw=[1],pv_pu=[0],dt_hours=.25,pv_kw=1)

def test_c2_not_falsely_implemented():
    with pytest.raises(NotImplementedError,match='C2'):
        build_energy_milp(scenario='Cenario_2',year=2026,load_kw=[1],pv_pu=[0],dt_hours=.25)

def test_c1_model_structure():
    pytest.importorskip('pyomo.environ')
    m=build_energy_milp(scenario='Cenario_1',year=2026,load_kw=[100,110],pv_pu=[0,.5],dt_hours=.25,pv_kw=20)
    assert len(m.T)==2
    assert m._rev02['pcc_kw']==2500
