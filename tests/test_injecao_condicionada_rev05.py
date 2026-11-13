from pathlib import Path
import pytest
from d28.traceability.controlled_injection import inject_conditional
BASE = Path(__file__).resolve().parents[1] / 'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'
COMMON = {'pcc_cap_kw': 1800., 'dt_hours': 0.5, 'pv_capacity_kw': 100.}
CHP = {'electrical_efficiency': 0.3, 'fuel_lhv_kwh_per_nm3': 6.}

def test_explicit_conditional_values_and_provenance():
    r = inject_conditional(BASE, selected_ids=['D05-001','D13-001','D09-002','D09-005','D08-001'], common=COMMON, chp=CHP)
    assert r['common']['pcc_cap_kw'] == 2500
    assert r['common']['dt_hours'] == 0.25
    assert r['chp_by_route']['R2']['fuel_lhv_kwh_per_nm3'] == 6
    assert r['chp_by_route']['R1']['fuel_lhv_kwh_per_nm3'] == 9.5
    assert r['chp_by_route']['R3']['fuel_lhv_kwh_per_nm3'] == 9.5
    assert all(r['chp_by_route'][route]['electrical_efficiency'] == .35 for route in ('R1','R2','R3'))
    assert not r['audit']['scientific_approval']
    assert len(r['audit']['base_master_sha256']) == 64

def test_inputs_are_not_mutated():
    c, ch = dict(COMMON), dict(CHP)
    inject_conditional(BASE, selected_ids=['D05-001'], common=c, chp=ch)
    assert c == COMMON and ch == CHP

def test_unmapped_or_unapproved_id_fails_closed():
    for id_ in ('D02-002','D11-015','D99-999'):
        with pytest.raises(ValueError):
            inject_conditional(BASE, selected_ids=[id_], common=COMMON, chp=CHP)

def test_duplicate_and_invalid_purpose_fail():
    with pytest.raises(ValueError):
        inject_conditional(BASE, selected_ids=['D05-001','D05-001'], common=COMMON, chp=CHP)
    with pytest.raises(ValueError):
        inject_conditional(BASE, selected_ids=[], common=COMMON, chp=CHP, purpose='ANNUAL')

def test_no_implicit_injection():
    r = inject_conditional(BASE, selected_ids=[], common=COMMON, chp=CHP)
    assert r['common'] == COMMON and r['audit']['injections'] == []
