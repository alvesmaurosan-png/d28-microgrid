import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/construir_entradas_anuais_f1_f3.py'
s=importlib.util.spec_from_file_location('contratos_anuais',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_contract_structure():
    r=m.build()
    assert len(r['years'])==20
    assert len(r['parameter_registry'])==137
    assert all(x['annual_pkm'] is None for x in r['years'])
    assert all(x['annual_grid_import_kwh_by_architecture']['R0'] is None for x in r['years'])
    assert r['F1'] is None and r['F3'] is None
    assert set(r['lca_required_factor_records'])=={'D11-014','D11-015','D11-016','D11-018','D11-019'}
