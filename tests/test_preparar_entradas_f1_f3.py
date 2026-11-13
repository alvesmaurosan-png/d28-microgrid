import importlib.util
from pathlib import Path

def test_export_does_not_fabricate_annual_series():
    p=Path(__file__).resolve().parents[1]/'scripts/preparar_entradas_f1_f3.py'
    spec=importlib.util.spec_from_file_location('f1f3_inputs',p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    data=mod.prepare()
    assert len(data['parameters'])==137
    assert data['annual_cashflows_brl'] is None
    assert data['annual_pkm'] is None
    assert data['lifecycle_ghg_components_kgco2e'] is None
    assert any(x['id']=='D11-014' and x['value_type']=='non_numeric_or_unquantified' for x in data['parameters'])
