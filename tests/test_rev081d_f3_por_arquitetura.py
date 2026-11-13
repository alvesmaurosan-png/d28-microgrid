import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from auditar_f3_rev081d import audit_architecture,FACTOR_MAP

def test_architecture_specific_missing_factors():
    records={k:{'value':None} for ids in FACTOR_MAP.values() for k in ids}
    a=audit_architecture('R0',records)
    assert 'D11-015' not in a['factors'] and 'D11-016' not in a['factors']
    assert 'D11-015' in audit_architecture('R3',records)['factors']
    assert 'D11-016' in audit_architecture('R2',records)['factors']

def test_r3_cgob_no_substitution():
    records={k:{'value':1} for ids in FACTOR_MAP.values() for k in ids}
    a=audit_architecture('R3',records,annual_fuel_nm3=100,cgob_coverage_nm3=80)
    assert a['cgob']['physical_fuel']=='NATURAL_GAS'
    assert a['cgob']['physical_emission_deduction_kgco2e']==0
    assert a['F3_kgco2e_per_pkm'] is None

def test_no_unverified_f3():
    records={k:{'value':1} for ids in FACTOR_MAP.values() for k in ids}
    for arch in FACTOR_MAP:
        assert audit_architecture(arch,records)['F3_kgco2e_per_pkm'] is None

def test_cgob_overcoverage_detected():
    records={k:{'value':1} for ids in FACTOR_MAP.values() for k in ids}
    a=audit_architecture('R3',records,annual_fuel_nm3=10,cgob_coverage_nm3=20)
    assert 'CGOB_COVERAGE_EXCEEDS_PHYSICAL_NATURAL_GAS_CONSUMPTION' in a['blockers']
