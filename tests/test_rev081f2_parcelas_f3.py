import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.fechar_parcelas_f3_rev081f2 import evaluate,verified_annual

ROOT=Path(__file__).resolve().parents[1]
def baseline():return json.loads((ROOT/'reports/D28_REV08_1F1_EVIDENCIAS_RECUPERADAS_F3.json').read_text(encoding='utf-8-sig'))
def test_preserves_23_roots_57_records():
    r=evaluate(baseline(),None)
    assert r['input_roots']==23 and r['original_records']==57
    assert r['root_status_counts']=={'PENDENTE':23}
def test_r0_grid_partial_only_with_valid_annual():
    annual={'status':'OPTIMAL','experiment':'R0_ANNUAL_A_E100','grid_energy_kwh':100}
    r=evaluate(baseline(),annual)
    p=[x for x in r['partial_calculations'] if x['parcel']=='grid_20y']
    assert len(p)==1 and p[0]['architecture']=='R0' and abs(p[0]['kgco2e']-199.2)<1e-8
    assert r['root_status_counts']=={'PENDENTE':23}
def test_r0_assets_only_when_design_verified():
    annual={'status':'OPTIMAL','experiment':'R0_ANNUAL_A_E100','grid_energy_kwh':100,'pv_kw':10,'bess_kwh':20}
    r=evaluate(baseline(),annual)
    assert {p['parcel'] for p in r['partial_calculations']}=={'grid_20y','PV_initial','BESS_initial'}
    assert not any(p['architecture']!='R0' for p in r['partial_calculations'])
def test_no_cgob_credit():
    r=evaluate(baseline(),None)
    assert r['r3_policy'].endswith('NO_AUTO_DEDUCTION') and not r['f3_complete']
