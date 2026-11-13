from pathlib import Path
import pytest
from d28.traceability.physical_rev052 import conditional_r2_sizing

BASE=Path(__file__).resolve().parents[1]/'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'

def sizing(**changes):
    args=dict(substrate_t_per_day=10.,chp_capacity_kw=60.,electrical_efficiency=.35,
              fuel_lhv_kwh_per_nm3=6.,dt_hours=.25,intervals=96)
    args.update(changes)
    return conditional_r2_sizing(BASE,**args)

def test_biogas_yield_converts_methane_to_raw_gas():
    v=sizing()
    assert v['derived']['biogas_nm3_per_day']==pytest.approx(1000.)
    assert sum(v['biogas']['production_nm3'])==pytest.approx(1000.)

def test_digester_volume_from_hydraulic_retention():
    assert sizing()['derived']['digester_geometric_m3']==pytest.approx(375.)

def test_gasometer_autonomy_from_rated_chp_fuel():
    v=sizing()
    assert v['derived']['gasometer_capacity_nm3']==pytest.approx(60/(.35*6)*8)
    assert v['biogas']['initial_gas_nm3']==pytest.approx(v['biogas']['gasometer_capacity_nm3']/2)

def test_auxiliary_and_chp_minimum_are_bound_and_not_approved():
    v=sizing()
    assert v['biogas']['auxiliary_fraction_chp_gross']==pytest.approx(.05)
    assert v['biogas']['minimum_load_fraction']==pytest.approx(.5)
    assert v['audit']['scientific_approval'] is False
    assert v['audit']['nsga2']=='BLOCKED'

def test_invalid_assumptions_fail_closed():
    for changes in ({'substrate_t_per_day':-1.},{'dt_hours':0.},
                    {'initial_stock_fraction':1.1},{'intervals':0}):
        with pytest.raises(ValueError):sizing(**changes)
