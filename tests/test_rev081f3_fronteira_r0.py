import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/completar_acv_r0_rev081f3.py'
spec=importlib.util.spec_from_file_location('rev081f3',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixture():
 return {'recovered_existing_factors':[]},{'partial_calculations':[{'architecture':'R0','parcel':'PV_initial','kgco2e':10,'factor':{'id':'D11-003'},'activity':{'value':1}}]}

def test_no_fake_factors():
 a,b=fixture();o=m.audit(a,b)
 assert o['f3_r0_complete'] is False
 assert sum(x['status']=='CALCULADA_CONDICIONAL' for x in o['parcels'])==1
 assert any(x['parcel']=='PCS_fabricacao' and x['status']=='PENDENTE' for x in o['parcels'])

def test_subtotal_only_calculated():
 a,b=fixture();assert m.audit(a,b)['partial_subtotal_kgco2e']==10

def test_legacy_not_automatically_accepted():
 a,b=fixture();o=m.audit(a,b)
 x=next(x for x in o['parcels'] if x['parcel']=='reposicao_BESS')
 assert x['status']=='PENDENTE' and any('D07-016' in s for s in x['missing'])

def test_no_r3_or_pareto():
 a,b=fixture();o=m.audit(a,b)
 assert o['architecture']=='R0' and not o['pareto_eligible']
