from pathlib import Path
import pytest
from d28.traceability.physical_parameterization import parameterize_physical, UNRESOLVED
BASE=Path(__file__).resolve().parents[1]/'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'
COMMON={'pv_capacity_kw':100.,'bess_capacity_kwh':100.,'pcs_power_kw':40.,'pcc_cap_kw':2500.,'dt_hours':.25}
CHP={'chp_capacity_kw':60.,'electrical_efficiency':.3,'fuel_lhv_kwh_per_nm3':6.}

def test_full_conditional_mapping():
    x=parameterize_physical(BASE,common=COMMON,chp=CHP)
    assert len(x['audit']['selected_ids'])==15
    assert x['common']['pv_capacity_max_kwp']==1908.225
    assert x['common']['eta_charge']==pytest.approx(.922)
    assert x['common']['eta_discharge']==pytest.approx(.922)
    assert x['common']['initial_soc']==pytest.approx(.5)
    assert x['checks']['bess_max_c_rate_per_hour']==pytest.approx(.55)
    assert not x['audit']['scientific_approval']
    assert x['audit']['annualization']=='BLOCKED'

def test_input_not_mutated():
    c=dict(COMMON); h=dict(CHP)
    parameterize_physical(BASE,common=c,chp=h)
    assert c==COMMON and h==CHP

def test_reject_unknown_and_annual():
    with pytest.raises(ValueError):
        parameterize_physical(BASE,common=COMMON,chp=CHP,selected_ids=['D08-013'])
    with pytest.raises(ValueError):
        parameterize_physical(BASE,common=COMMON,chp=CHP,purpose='ANNUAL')

def test_reject_invalid_pv_design():
    with pytest.raises(ValueError):
        parameterize_physical(BASE,common=dict(COMMON,pv_capacity_kw=9999),chp=CHP)

def test_unresolved_documented():
    assert 'D09-004' in UNRESOLVED and 'D08-013' in UNRESOLVED
