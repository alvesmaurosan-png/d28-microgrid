import importlib.util
from pathlib import Path
import json
p=Path(__file__).resolve().parents[1]/'scripts/calcular_parcelas_f1_f3_rev02.py'
spec=importlib.util.spec_from_file_location('parcelas',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_calculo_sem_anualizacao():
    fixture=Path(__file__).resolve().parents[1]/'reports/D28_CONTRATOS_ANUAIS_F1_F3_INTEGRADOS_REV01.json'
    if not fixture.exists():return
    d=m.calc(json.loads(fixture.read_text(encoding='utf-8')))
    assert d['F1'] is None and d['F3'] is None
    assert not d['annualized_R0_R3']
    for s in d['synthetic_reference_scenarios'].values():
        assert s['grid_bill_brl'] is None
        assert s['full_F3'] is None
