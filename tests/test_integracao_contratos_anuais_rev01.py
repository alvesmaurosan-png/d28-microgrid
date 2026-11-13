import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/integrar_contratos_anuais_f1_f3_rev01.py'
spec=importlib.util.spec_from_file_location('integration',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_real_contract_without_dispatch_mutation():
    if not m.SOURCE.exists():return
    import json
    src=json.loads(m.SOURCE.read_text(encoding='utf-8'))
    out=m.integrate(src)
    assert out['F1'] is None and out['F3'] is None
    assert len(out['years'])==20
    assert all(x['annual_pkm'] is None for x in out['years'])
    assert all(all(v is None for v in x['annual_grid_import_kwh_by_architecture'].values()) for x in out['years'])
    assert out['service_reference']['pkm_per_bus_year_conditional']==1376757.0
    assert out['annual_synthetic_reference_scenarios']['E100']['annual_pkm_reference_conditional']==137675700.0
