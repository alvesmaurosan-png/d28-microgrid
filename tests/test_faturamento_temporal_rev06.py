import csv
import hashlib
import importlib.util
from pathlib import Path

SPEC=importlib.util.spec_from_file_location('rev06',Path(__file__).resolve().parents[1]/'scripts/integrar_faturamento_temporal_rev06.py')
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)

def fixtures(tmp_path):
    csv_path=tmp_path/'temporal.csv'
    with csv_path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['interval_index','interval_start_local','month','grid_kw'])
        w.writeheader()
        w.writerow(dict(interval_index=0,interval_start_local='2026-01-01T00:00:00',month='2026-01',grid_kw=100))
        w.writerow(dict(interval_index=1,interval_start_local='2026-01-01T00:15:00',month='2026-01',grid_kw=200))
    validation=dict(status='TEMPORAL_EXPORT_VALIDATED_CONDITIONAL',series_sha256=mod.sha256(csv_path),evidence='SYNTHETIC_COUNTERFACTUAL_NOT_HOMOLOGATED',dt_hours=0.25,intervals=2,grid_energy_kwh=75,grid_peak_kw=200,monthly={'2026-01':{'intervals':2,'energy_kwh':75,'peak_kw':200}})
    rev04={'case':'R0_A_E100','status':'CONDITIONAL_EXPLORATORY_NOT_HOMOLOGATED','F1_components':{'energy_purchase_flat_tariff_exploratory_brl_year':56.25},'dispatch':{'grid_import_kwh_year':75}}
    config={'status':'EXPLORATORY_NOT_HOMOLOGATED','currency':'BRL_2026_real','energy_tariff_brl_per_kwh':0.75,'demand_tariff_brl_per_kw_month':30}
    return csv_path,validation,rev04,config

def test_monthly_physical_and_exploratory(tmp_path):
    r=mod.integrate(*fixtures(tmp_path),require_annual=False)
    assert r['annual']['grid_import_kwh']==75
    assert r['annual']['physical_peak_kw']==200
    assert r['annual']['flat_energy_cost_exploratory_brl']==56.25
    assert r['annual']['contractual_demand_charge_brl'] is None
    assert r['months'][0]['billable_demand_kw'] is None

def test_reject_tampered_series(tmp_path):
    p,v,r,c=fixtures(tmp_path)
    p.write_text(p.read_text().replace(',200\n',',300\n'))
    import pytest
    with pytest.raises(ValueError,match='SHA-256'):
        mod.integrate(p,v,r,c,require_annual=False)

def test_reject_nonreconciled_rev04(tmp_path):
    p,v,r,c=fixtures(tmp_path)
    r['F1_components']['energy_purchase_flat_tariff_exploratory_brl_year']=99
    import pytest
    with pytest.raises(ValueError,match='REV04'):
        mod.integrate(p,v,r,c,require_annual=False)
