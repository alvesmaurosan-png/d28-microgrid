import csv,hashlib,importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('rev07',Path(__file__).resolve().parents[1]/'scripts/avaliar_tarifas_temporais_rev07.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def fixture(tmp_path):
 p=tmp_path/'series.csv'
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['interval_index','interval_start_local','month','grid_kw']);w.writeheader()
  w.writerow(dict(interval_index=0,interval_start_local='2026-01-05T18:00:00',month='2026-01',grid_kw=100))
  w.writerow(dict(interval_index=1,interval_start_local='2026-01-05T18:15:00',month='2026-01',grid_kw=200))
 rev={'status':'MONTHLY_PHYSICAL_RECONCILED_FLAT_TARIFF_EXPLORATORY','sources':{'temporal_csv':{'sha256':mod.digest(p)}},'intervals':2,'annual':{'grid_import_kwh':75,'physical_peak_kw':200},'months':[{'month':'2026-01','intervals':2,'energy_kwh':75,'physical_peak_kw':200}]}
 cfg={'classification':'SYNTHETIC_EXPLORATORY_NOT_HOMOLOGATED','scenarios':[{'id':'flat','model':'flat','offpeak_brl_kwh':0.75,'peak_brl_kwh':0.75,'contracted_demand_kw':250,'demand_rate_brl_kw_month':30},{'id':'tou','model':'synthetic_weekday_tou','offpeak_brl_kwh':0.15,'peak_brl_kwh':2,'contracted_demand_kw':150,'demand_rate_brl_kw_month':30,'peak_start_hour':18,'peak_end_hour':21}]}
 evid={'classification':'DOCUMENTARY_EVIDENCE_INVENTORY_NOT_CONTRACT_VALIDATION','contract_status':'NOT_DOCUMENTED'}
 return p,rev,cfg,evid
def test_scenarios_and_documented_null(tmp_path):
 r=mod.calc(*fixture(tmp_path),annual=False)
 a,b=r['exploratory']['scenarios']
 assert a['annual']['energy_cost_exploratory_brl']==56.25
 assert a['annual']['demand_proxy_brl']==7500
 assert b['annual']['peak_kwh']==75
 assert b['annual']['energy_cost_exploratory_brl']==150
 assert b['annual']['demand_proxy_brl']==6000
 assert r['documented_contract']['total_bill_brl'] is None
 assert r['F1'] is None
def test_reject_modified_series(tmp_path):
 p,rev,cfg,evid=fixture(tmp_path)
 p.write_text(p.read_text().replace(',200\n',',201\n'))
 with pytest.raises(ValueError,match='SHA'):mod.calc(p,rev,cfg,evid,annual=False)
def test_reject_unverified_contract(tmp_path):
 p,rev,cfg,evid=fixture(tmp_path)
 evid['contract_status']='VERIFIED'
 with pytest.raises(ValueError,match='Evidência contratual'):mod.calc(p,rev,cfg,evid,annual=False)
def test_reject_invalid_tariff(tmp_path):
 p,rev,cfg,evid=fixture(tmp_path)
 cfg['scenarios'][0]['demand_rate_brl_kw_month']=-1
 with pytest.raises(ValueError,match='Coeficiente'):mod.calc(p,rev,cfg,evid,annual=False)
