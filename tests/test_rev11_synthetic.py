import sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from d28.optimization.synthetic_reference_rev11 import make_contract,check_contract,make_prices,read_series,precheck_r0,read_json
from datetime import datetime

def test_contract_separate_and_complete():
 c=make_contract();assert check_contract(c);assert len(c['source_day_for_calendar_day'])==365
 c['scope']='OBSERVED';
 try:check_contract(c);assert False
 except ValueError:pass

def test_tou():
 import pytest
 pytest.importorskip("pyomo")
 cfg={'model':'synthetic_weekday_tou','peak_start_hour':18,'peak_end_hour':21,'peak_brl_kwh':2.,'offpeak_brl_kwh':.15}
 prices=make_prices([datetime(2025,1,6,18),datetime(2025,1,5,18)],cfg)
 assert prices.grid_brl_kwh==(2.,.15)

def test_annual_data_and_pcc():
 c=make_contract();i,a=read_series(ROOT,'E100',c)
 assert a['n']==35040 and len(i.months)==35040
 class Econ:pcc_import_limit_kw=2500.
 r=precheck_r0(i,Econ(),{'pv_kw':1908.225,'pcs_kw':0})
 assert r['instant_power_necessary_condition_failed']

def test_old_contract_unchanged():
 old=read_json(ROOT/'contrato_anual.json')
 assert old['status']=='PENDING_RESEARCHER_APPROVAL'
