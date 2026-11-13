"""D28 REV11: cenário sintético autorizado; MILP físico legado intacto.
Nenhuma aprovação de dados observados é inferida; contrato histórico preservado.
"""
from __future__ import annotations
import csv, json, math, hashlib, calendar
from pathlib import Path
from datetime import datetime, date, timedelta
from dataclasses import replace
from d28.optimization.r0_r3_bridge import annual_contract_ready
from d28.optimization.biobjective_milp_connector import ConnectorInputs
from d28.economics.f1 import Economics
from d28.optimization.annual_accounting_r0_r3 import AnnualAccounting
from d28.optimization.annual_f1_f2_reconciled_rev09 import annual_f1_f2_reconciled

SCENARIOS={'E100':100,'E200':200,'E300':300,'E375':375,'E450':450}
ROUTES=('R0','R1','R2','R3')

def sha(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def check_contract(contract):
 if contract.get('scope')!='SYNTHETIC_COUNTERFACTUAL_ONLY' or contract.get('researcher_authorization')!='EXPLICIT_2026-10-28':
  raise ValueError('SYNTHETIC_RESEARCHER_AUTHORIZATION_REQUIRED')
 ready,why=annual_contract_ready(contract)
 if not ready:raise ValueError('SYNTHETIC_CONTRACT_INVALID: '+why)
 if contract.get('mapping_method')!='SYNTHETIC_CALENDAR_POSITION_NOT_OBSERVED':
  raise ValueError('MAPPING_METHOD_INVALID')
 return True

def make_contract(year=2025):
 first=date(year,1,1);last=date(year+1,1,1)
 mapping={(first+timedelta(days=i)).isoformat():(first+timedelta(days=i)).isoformat() for i in range((last-first).days)}
 return {'status':'APPROVED','scope':'SYNTHETIC_COUNTERFACTUAL_ONLY','researcher_authorization':'EXPLICIT_2026-10-28',
  'year':year,'timezone':'America/Sao_Paulo','model':'REUSE_COMPLETE_SOURCE_DAYS_BY_EXPLICIT_MAP',
  'interpretation':'SYNTHETIC_COUNTERFACTUAL_NOT_OBSERVED','load_semantics':'CHARGING_AC_ONLY_NO_NON_VEHICLE_LOAD',
  'mapping_method':'SYNTHETIC_CALENDAR_POSITION_NOT_OBSERVED','mapping_evidence_status':'APPROVED',
  'calendar_mapping_rationale':'Mapa explícito 2025→posição sintética correspondente; não representa medição solar e carga simultâneas, nem comprova representatividade operacional.',
  'source_day_for_calendar_day':mapping}

def read_series(root,scenario,contract):
 check_contract(contract)
 if scenario not in SCENARIOS:raise ValueError('INVALID_SCENARIO')
 path=Path(root)/f'data/processed/milp_inputs/R0_inputs_{scenario}_15min.csv'
 n=(8784 if calendar.isleap(contract['year']) else 8760)*4
 load=[];pv=[];months=[];bad=[];first=datetime(contract['year'],1,1)
 with path.open(newline='',encoding='utf-8-sig') as f:
  for i,r in enumerate(csv.DictReader(f)):
   stamp=datetime.fromisoformat(r['interval_start_local'])
   expected=first+timedelta(minutes=15*i)
   if stamp!=expected or int(r['interval_index'])!=i or r['scenario']!=scenario:bad.append(i)
   a=float(r['load_charging_ac_kw']);b=float(r['pv_kw_per_kwp']);dt=float(r['dt_hours'])
   if not all(math.isfinite(x) and x>=0 for x in (a,b)) or abs(dt-.25)>1e-12:bad.append(i)
   load.append(a);pv.append(b);months.append(stamp.year*100+stamp.month)
 if len(load)!=n or bad:raise ValueError(f'INVALID_15MIN_SERIES n={len(load)} bad={bad[:5]}')
 return ConnectorInputs(tuple(load),tuple(pv),tuple(months),.25),{'path':str(path.relative_to(root)),'sha256':sha(path),'n':n,'energy_kwh':sum(load)*.25,'peak_kw':max(load)}

def make_prices(instants,tariff):
 from d28.optimization.economic_dispatch_f1f2 import EnergyPrices
 if tariff['model']=='flat':return EnergyPrices(tuple(float(tariff['offpeak_brl_kwh']) for _ in instants))
 if tariff['model']!='synthetic_weekday_tou':raise ValueError('INVALID_TARIFF_MODEL')
 start,end=int(tariff['peak_start_hour']),int(tariff['peak_end_hour'])
 prices=[]
 for t in instants:
  peak=t.weekday()<5 and start<=t.hour<end
  prices.append(float(tariff['peak_brl_kwh'] if peak else tariff['offpeak_brl_kwh']))
 return EnergyPrices(tuple(prices))

def load_reference(root,scenario,route,settings):
 root=Path(root);contract=read_json(root/settings['contract_path']);check_contract(contract)
 inputs,series_audit=read_series(root,scenario,contract)
 tariffs=read_json(root/settings['tariffs_path'])['scenarios'];tariff=next(t for t in tariffs if t['id']==settings['tariff_id'])
 times=(datetime(contract['year'],1,1)+timedelta(minutes=15*i) for i in range(len(inputs.load_kw)))
 grid_prices=make_prices(times,tariff)
 # Specific costs of R1-R3 MUST be provided; never silently set fuel or CHP CAPEX to zero.
 if route!='R0':
  rc=settings.get('routes',{}).get(route,{})
  required=['route_options','fuel_brl_nm3','incremental_present_value_brl','evidence']
  if any(k not in rc or rc[k] is None for k in required):raise ValueError(f'{route}_ASSUMPTIONS_REQUIRED: '+','.join(required))
  opts=rc['route_options'];inputs=replace(inputs,route_options=opts)
  from d28.optimization.economic_dispatch_f1f2 import EnergyPrices
  grid_prices=EnergyPrices(grid_prices.grid_brl_kwh,float(rc['fuel_brl_nm3']),
   float(rc.get('production_brl_nm3',0)),float(rc.get('gas_loss_brl_nm3',0)),
   float(rc.get('auxiliary_incremental_brl_kwh',0)),bool(rc.get('fuel_cost_includes_production',False)))
  if route=='R2' and 'production_nm3' not in opts:raise ValueError('R2_ANNUAL_PRODUCTION_REQUIRED')
  if route=='R3' and not rc.get('cgob_accounting_rule'):raise ValueError('R3_CGOB_RULE_REQUIRED')
  accounting=AnnualAccounting(incremental_present_value_brl=float(rc['incremental_present_value_brl']),
   evidence=rc['evidence'],cgob_accounting_rule=rc.get('cgob_accounting_rule'))
 else:accounting=AnnualAccounting()
 econ=Economics.from_json(root/settings['economics_path'])
 econ=replace(econ,demand_tariff_brl_per_kw_month=float(tariff['demand_rate_brl_kw_month']))
 operation=settings['pkm_assumptions'];fleet=SCENARIOS[scenario]
 pkm=fleet*float(operation['km_per_bus_day'])*float(operation['passengers_per_bus_km'])*int(operation['operating_days_per_year'])
 if pkm<=0:raise ValueError('INVALID_SYNTHETIC_PKM')
 if route=='R2' and grid_prices.auxiliary_incremental_brl_kwh and not settings.get('auxiliary_incremental_verified',False):
  raise ValueError('AUXILIARY_DOUBLE_COUNT_RISK')
 provenance={'series':series_audit,'contract_sha256':sha(root/settings['contract_path']),
  'economics_sha256':sha(root/settings['economics_path']),
  'tariffs_sha256':sha(root/settings['tariffs_path']),
  'assumptions':settings['pkm_assumptions'],'tariff_id':tariff['id'],
  'classification':'SYNTHETIC_COUNTERFACTUAL_NOT_OBSERVED'}
 return contract,inputs,grid_prices,econ,accounting,pkm,provenance

def precheck_r0(inputs,econ,design):
 # Necessary energy condition, assuming 100% capture of PV and zero BESS losses.
 energy=sum(inputs.load_kw)*inputs.dt_hours
 solar=sum(inputs.pv_pu)*inputs.dt_hours*float(design['pv_kw'])
 grid_max=econ.pcc_import_limit_kw*len(inputs.load_kw)*inputs.dt_hours
 impossible=energy>solar+grid_max+1e-6
 # Instantaneous bound: BESS cannot discharge beyond PCS. Conservative necessary condition.
 max_support=max(float(design['pv_kw'])*p+float(design['pcs_kw'])+econ.pcc_import_limit_kw for p in inputs.pv_pu)
 instant_impossible=any(l>econ.pcc_import_limit_kw+float(design['pv_kw'])*p+float(design['pcs_kw'])+1e-6 for l,p in zip(inputs.load_kw,inputs.pv_pu))
 return {'energy_demand_kwh':energy,'max_pv_kwh':solar,'max_grid_kwh':grid_max,
  'annual_energy_necessary_condition_failed':impossible,'instant_power_necessary_condition_failed':instant_impossible,
  'feasibility_not_proven':not(impossible or instant_impossible)}

def evaluate(root,scenario,route,design,settings,*,run_solver=False,solver_name='appsi_highs'):
 if route not in ROUTES:raise ValueError('INVALID_ROUTE')
 contract,inputs,prices,econ,accounting,pkm,prov=load_reference(root,scenario,route,settings)
 if design['pv_kw']>econ.pv_capacity_max_kwp:raise ValueError('ROOF_PV_LIMIT')
 if design['pcs_kw']>econ.bess_max_c_rate_per_hour*design['bess_kwh']:raise ValueError('BESS_C_RATE_LIMIT')
 audit={'route':route,'scenario':scenario,'design':design,'annual_pkm':pkm,'provenance':prov,
        'contract_scope':'SYNTHETIC_COUNTERFACTUAL_ONLY','objectives':None,'n_obj':2,'f3_excluded':True}
 if route=='R0':
  physical=precheck_r0(inputs,econ,design);audit['necessary_feasibility']=physical
  if physical['annual_energy_necessary_condition_failed'] or physical['instant_power_necessary_condition_failed']:
   return dict(audit,status='PROVEN_INFEASIBLE_NECESSARY_CONDITION',milp_executed=False)
 if not run_solver:return dict(audit,status='PREFLIGHT_ONLY',milp_executed=False)
 from d28.optimization.economic_dispatch_f1f2 import solve_economic
 solved=solve_economic(route,design,inputs,prices,solver_name=solver_name)
 if solved['status']!='PASS':return dict(audit,status='MILP_FAILED',milp_executed=True,solver_reason=solved.get('reason'),solver_exception=solved.get('solver_exception'),solver_termination=solved.get('termination_condition'))
 result=annual_f1_f2_reconciled(route,cfg=econ,design=design,grid_kw=solved['grid_kw'],
  months=inputs.months,dt_hours=inputs.dt_hours,prices=prices,annual_pkm=pkm,
  accounting=accounting,contract=contract,dispatch_components=solved['cost_components_brl'],
  evidence_approved=True,provenance=json.dumps(prov,ensure_ascii=False))
 return dict(audit,status='OPTIMAL_SYNTHETIC',milp_executed=True,objectives=list(result['objectives']),
  units=list(result['units']),accounting_audit=result['audit'],solver_checks=solved['checks'])

def make_problem(root,scenario,route,settings,bounds,solver_name='appsi_highs'):
 from d28.optimization.biobjective_f1_f2 import make_pymoo_problem, BiobjectiveResult
 def candidate(design):
  try:
   r=evaluate(root,scenario,route,design,settings,run_solver=True,solver_name=solver_name)
   return BiobjectiveResult(route,r['status']=='OPTIMAL_SYNTHETIC',tuple(r['objectives']) if r['objectives'] else None,r['status'],r)
  except Exception as exc:
   return BiobjectiveResult(route,False,None,'EVALUATION_ERROR',{'error':str(exc)})
 return make_pymoo_problem(route,bounds,candidate)
