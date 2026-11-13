"""REV07: cenários tarifários exploratórios separados de evidência contratual D28."""
import csv,hashlib,json,math
from datetime import datetime,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CSV=ROOT/'results/r0_annual_validation/annual_A_E100_temporal_15min.csv'
REV06=ROOT/'reports/D28_FATURAMENTO_TEMPORAL_REV06.json'
CFG=ROOT/'config/tariffs/rev07_scenarios_exploratory.json'
EVID=ROOT/'config/tariffs/rev07_evidencias_contratuais.json'
OUT=ROOT/'reports/D28_AVALIACAO_TARIFARIA_REV07.json'
MONTHLY=ROOT/'reports/D28_AVALIACAO_TARIFARIA_CENARIOS_REV07.csv'

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def numeric(v,name):
 if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0:raise ValueError('Coeficiente inválido: '+name)
 return float(v)
def calc(series,rev06,config,evidence,*,annual=True):
 if rev06.get('status')!='MONTHLY_PHYSICAL_RECONCILED_FLAT_TARIFF_EXPLORATORY':raise ValueError('REV06 não validada')
 if rev06['sources']['temporal_csv']['sha256']!=digest(series):raise ValueError('SHA temporal diferente da REV06')
 if config.get('classification')!='SYNTHETIC_EXPLORATORY_NOT_HOMOLOGATED':raise ValueError('Configuração sem marcação exploratória')
 if evidence.get('classification')!='DOCUMENTARY_EVIDENCE_INVENTORY_NOT_CONTRACT_VALIDATION':raise ValueError('Inventário contratual inválido')
 if evidence.get('contract_status')!='NOT_DOCUMENTED':raise ValueError('Evidência contratual deve ser analisada antes de habilitar faturamento')
 scenarios=config['scenarios']
 if not scenarios or len({x['id'] for x in scenarios})!=len(scenarios):raise ValueError('IDs de cenários duplicados ou ausentes')
 for s in scenarios:
  if s['model'] not in ('flat','synthetic_weekday_tou'):raise ValueError('Modelo tarifário desconhecido')
  numeric(s['offpeak_brl_kwh'],'offpeak');numeric(s['peak_brl_kwh'],'peak')
  numeric(s['demand_rate_brl_kw_month'],'demand_rate')
  numeric(s['contracted_demand_kw'],'contracted_demand')
  if s['model']=='synthetic_weekday_tou':
   if not (0<=s['peak_start_hour']<s['peak_end_hour']<=24):raise ValueError('Janela de ponta inválida')
   if s['peak_start_hour']%0.25 or s['peak_end_hour']%0.25:raise ValueError('Ponta deve alinhar aos 15 minutos')
 records={s['id']:{} for s in scenarios}; total=0.;peak=0.;count=0;previous=None;months={}
 with Path(series).open(newline='',encoding='utf-8') as f:
  rdr=csv.DictReader(f)
  for row in rdr:
   if int(row['interval_index'])!=count:raise ValueError('Índice temporal inválido')
   ts=datetime.fromisoformat(row['interval_start_local'])
   if previous is not None and ts-previous!=timedelta(minutes=15):raise ValueError('Cronologia inválida')
   previous=ts;month=ts.strftime('%Y-%m')
   if month!=row['month']:raise ValueError('Mês incompatível')
   g=float(row['grid_kw'])
   if not math.isfinite(g) or g < -1e-7:raise ValueError('Potência de rede inválida')
   g=max(g,0.);e=g*0.25;count+=1;total+=e;peak=max(peak,g)
   m=months.setdefault(month,{'energy_kwh':0.,'physical_peak_kw':0.,'intervals':0})
   m['energy_kwh']+=e;m['physical_peak_kw']=max(m['physical_peak_kw'],g);m['intervals']+=1
   for s in scenarios:
    r=records[s['id']].setdefault(month,{'month':month,'peak_kwh':0.,'offpeak_kwh':0.,'physical_peak_kw':0.,'intervals':0})
    h=ts.hour+ts.minute/60
    ispeak=(s['model']=='synthetic_weekday_tou' and ts.weekday()<5 and s['peak_start_hour']<=h<s['peak_end_hour'])
    r['peak_kwh' if ispeak else 'offpeak_kwh']+=e
    r['physical_peak_kw']=max(r['physical_peak_kw'],g);r['intervals']+=1
 if count!=rev06['intervals'] or not math.isclose(total,rev06['annual']['grid_import_kwh'],abs_tol=0.01) or not math.isclose(peak,rev06['annual']['physical_peak_kw'],abs_tol=1e-5):raise ValueError('REV06 não reconciliada')
 if annual and (count!=35040 or len(months)!=12):raise ValueError('Ano incompleto')
 revmonths={x['month']:x for x in rev06['months']}
 if set(months)!=set(revmonths):raise ValueError('Meses divergentes')
 for k,m in months.items():
  ref=revmonths[k]
  if m['intervals']!=ref['intervals'] or not math.isclose(m['energy_kwh'],ref['energy_kwh'],abs_tol=0.01) or not math.isclose(m['physical_peak_kw'],ref['physical_peak_kw'],abs_tol=1e-5):raise ValueError('Divergência mensal REV06: '+k)
 outputs=[]
 for s in scenarios:
  rows=[]
  for m in records[s['id']].values():
   x=dict(m)
   x['energy_cost_exploratory_brl']=x['peak_kwh']*s['peak_brl_kwh']+x['offpeak_kwh']*s['offpeak_brl_kwh']
   x['demand_proxy_brl']=max(s['contracted_demand_kw'],x['physical_peak_kw'])*s['demand_rate_brl_kw_month']
   x['total_proxy_exploratory_brl']=x['energy_cost_exploratory_brl']+x['demand_proxy_brl']
   x['billable_demand_kw']=None;x['contractual_bill_brl']=None;x['overrun_charge_brl']=None
   if not math.isclose(x['peak_kwh']+x['offpeak_kwh'],months[x['month']]['energy_kwh'],abs_tol=0.01):raise ValueError('Erro na segregação temporal')
   rows.append(x)
  outputs.append({'scenario_id':s['id'],'model':s['model'],'assumptions':s,'months':rows,'annual':{'energy_cost_exploratory_brl':sum(x['energy_cost_exploratory_brl'] for x in rows),'demand_proxy_brl':sum(x['demand_proxy_brl'] for x in rows),'total_proxy_exploratory_brl':sum(x['total_proxy_exploratory_brl'] for x in rows),'peak_kwh':sum(x['peak_kwh'] for x in rows),'offpeak_kwh':sum(x['offpeak_kwh'] for x in rows),'contractual_bill_brl':None}})
 # Não habilitar faturamento documental sem prova verificável de modalidade, tarifas, contrato e regras.
 documented={'status':'CONTRACT_NOT_DOCUMENTED_NO_BILLING','contracted_demand_kw':None,'tariff_modality':None,'tariff_period_calendar':None,'energy_charge_brl':None,'demand_charge_brl':None,'overrun_charge_brl':None,'taxes_and_flags_brl':None,'total_bill_brl':None,'evidence_inventory':evidence.get('evidence_inventory',[]),'missing_evidence':evidence.get('missing_evidence',[])}
 return {'revision':'REV07','case':'R0_A_E100','status':'EXPLORATORY_SIMULATIONS_RECONCILED_CONTRACTUAL_NULL','source_sha256':digest(series),'intervals':count,'annual_grid_energy_kwh':total,'annual_physical_peak_kw':peak,'exploratory':{'status':'SYNTHETIC_EXPLORATORY_NOT_HOMOLOGATED','scenarios':outputs},'documented_contract':documented,'F1':None,'F3':None,'notes':['Janela de ponta sintética apenas em dias úteis, sem exclusão de feriados','Demanda proxy usa max(contratada hipotética, pico físico mensal) e não representa medição/faturamento real','Não inclui tributos, bandeiras, ultrapassagem, reativos, descontos nem componentes regulatórios','Cenários são comparações alternativas; não somar seus custos aos da REV04/REV06','Despacho é fixo: não há resposta ótima à tarifa simulada','Não presume homologação da garagem, da série sintética ou de contratos']}
def main():
 for p in (CSV,REV06,CFG,EVID):
  if not p.is_file():raise SystemExit('Arquivo ausente: '+str(p))
 result=calc(CSV,read(REV06),read(CFG),read(EVID))
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 with MONTHLY.open('w',encoding='utf-8',newline='') as f:
  cols=['scenario_id','month','intervals','peak_kwh','offpeak_kwh','physical_peak_kw','energy_cost_exploratory_brl','demand_proxy_brl','total_proxy_exploratory_brl']
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
  for s in result['exploratory']['scenarios']:
   for m in s['months']:w.writerow({'scenario_id':s['scenario_id'],**{k:m[k] for k in cols if k!='scenario_id'}})
 print('REV07:',result['status']);print('Intervalos:',result['intervals'],'| energia (kWh):',result['annual_grid_energy_kwh'])
 for s in result['exploratory']['scenarios']:
  print(s['scenario_id'],'| energia R$:',round(s['annual']['energy_cost_exploratory_brl'],2),'| proxy demanda R$:',round(s['annual']['demand_proxy_brl'],2),'| total proxy R$:',round(s['annual']['total_proxy_exploratory_brl'],2))
 print('Fatura contratual:',result['documented_contract']['total_bill_brl']);print('Relatórios:',OUT,MONTHLY)
if __name__=='__main__':main()
