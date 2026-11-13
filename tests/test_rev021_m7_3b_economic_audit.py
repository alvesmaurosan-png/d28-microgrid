import pytest
from d28.rev02.m7_3b_economic_audit import audit_f1

BASE=dict(fleet_brl=0,infrastructure_brl=100,grid_reinforcement_brl=20,
          energy_brl=30,operations_brl=10,residual_brl=5,discounted_pkm=100)

def test_m73b_reconciles_but_does_not_claim_full_audit():
    r=audit_f1(BASE,reported_f1=1.55)
    assert r['status']=='PENDING'
    assert r['f1_energy_infrastructure_brl_per_pkm']==pytest.approx(1.55)
    assert any(x['code']=='INTEGRATED_RECONCILIATION' and x['status']=='PASS' for x in r['checks'])
    assert not r['annual_authorized']

def test_m73b_detects_fleet_scope_mismatch():
    r=audit_f1({**BASE,'fleet_brl':100},reported_f1=2.55)
    assert r['status']=='FAIL'
    assert r['fleet_effect_brl_per_pkm']==pytest.approx(1)
    assert any(x['code']=='FLEET_SCOPE' and x['status']=='FAIL' for x in r['checks'])

def test_m73b_missing_inputs_pending():
    assert audit_f1({})['status']=='PENDING'

def test_m73b_invalid_pkm_fails():
    assert audit_f1({**BASE,'discounted_pkm':0})['status']=='FAIL'

def test_m73b_reported_mismatch_fails():
    assert audit_f1(BASE,reported_f1=2)['status']=='FAIL'
