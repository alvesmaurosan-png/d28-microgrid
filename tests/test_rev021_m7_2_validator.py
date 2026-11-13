import json
import pytest
from d28.rev02.contracts import Scenario
from d28.rev02.m7_validator import validate_one, validate_matrix, write_reports


def test_m7_matrix_has_12_scenario_year_pairs():
    r = validate_matrix()
    assert len(r['records']) == 12
    assert {(x['scenario'],x['year']) for x in r['records']} == {
        (s.value,y) for s in Scenario for y in (2026,2030,2038)}
    assert all(not x['annual_authorized'] for x in r['records'])


def test_m7_bau_no_fixed_pcc_and_grid_upgrade():
    r = validate_one(Scenario.BAU,2026)
    assert r['contract']['pcc_limit_kw'] is None
    assert r['contract']['grid_upgrade_allowed'] is True
    assert r['contract']['local_pv_bess_chp'] is False


def test_m7_realista_rejects_local_generation():
    r = validate_one(Scenario.REALISTA,2026,design={
        'pv_kw':1,'bess_kwh':0,'pcs_kw':0,'chp_kw':0})
    assert next(x for x in r['checks'] if x['code']=='DESIGN')['status']=='FAIL'


def test_m7_c2_fleet_mix_and_2038_requirement():
    ok = validate_one(Scenario.C2,2026,fleet={'bev':200,'diesel':250,'gas':0})
    assert next(x for x in ok['checks'] if x['code']=='FLEET')['status']=='PASS'
    bad = validate_one(Scenario.C2,2038,fleet={'bev':300,'diesel':150,'gas':0})
    assert next(x for x in bad['checks'] if x['code']=='FLEET')['status']=='PASS'
    # O contrato C2 não impõe enforce_all_bev_in_2038: não inventar essa regra.
    assert bad['contract']['enforce_all_bev_in_2038'] is False


def test_m7_missing_operational_inputs_never_passes():
    r = validate_one(Scenario.C1,2026)
    assert r['status'] != 'PASS'
    assert any(x['status']=='PENDING' for x in r['checks'])


def test_m7_false_evidence_does_not_fail():
    r = validate_one(Scenario.C1,2026,evidence={'discounted_pkm_verified':False})
    assert r['status'] == 'PENDING'
    assert not any(x['code'].startswith('EVIDENCE.') for x in r['checks'])


def test_m7_annual_always_blocked():
    r = validate_one(Scenario.C1,2026,request_annual=True)
    assert next(x for x in r['checks'] if x['code']=='ANNUAL_EXECUTION')['status']=='BLOCKED'


def test_m7_reports_json_csv(tmp_path):
    report = validate_matrix()
    jp,cp = write_reports(report,tmp_path)
    assert len(json.loads(jp.read_text(encoding='utf-8'))['records']) == 12
    assert cp.read_text(encoding='utf-8-sig').count('\n') > 12


def test_m7_rejects_unsupported_year():
    with pytest.raises(ValueError):
        validate_one(Scenario.C1,2050)


def test_m7_evidence_ignored_in_matrix():
    r = validate_matrix({'Cenario_1': {'2026': {'evidence': {'discounted_pkm_verified': False}}}})
    row = next(x for x in r['records'] if x['scenario'] == 'Cenario_1' and x['year'] == 2026)
    assert row['status'] == 'PENDING'
    assert not any(c['code'].startswith('EVIDENCE.') for c in row['checks'])
