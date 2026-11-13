#!/usr/bin/env python3
"""Calendário anual sintético EXPLÍCITO, usando sucessores e deslocamentos documentados.
Não é reconstituição da frota real; não executa solver e não homologa cientificamente.
"""
import argparse,csv,datetime,hashlib,json,math
from pathlib import Path
SCENARIOS={'E100':100,'E200':200,'E300':300,'E375':375,'E450':450}
N=365*96; DT=15; ETA=.94; POWER=138.
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def load_csv(path):
 with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writer(path,fields):
 f=open(path,'w',encoding='utf-8-sig',newline='');w=csv.DictWriter(f,fieldnames=fields);w.writeheader();return f,w
def main():
 p=argparse.ArgumentParser();p.add_argument('--sessoes',required=True);p.add_argument('--transicoes',required=True);p.add_argument('--out',required=True);p.add_argument('--ano',type=int,default=2025);a=p.parse_args()
 if a.ano!=2025:raise SystemExit('Esta implementação está fixada em 2025 civil, 365 dias.')
 src=Path(a.sessoes);trans=Path(a.transicoes);out=Path(a.out)
 if out.exists() and any(out.iterdir()):raise SystemExit('Saída já contém arquivos; escolha diretório novo.')
 out.mkdir(parents=True,exist_ok=True)
 sessions=load_csv(src);T=json.loads(trans.read_text(encoding='utf8'))
 B={r['block_id']:r for r in sessions}
 assert len(B)==115 and set(B)==set(T),'Cobertura de 115 blocos/transições não conciliada'
 for b,t in T.items():
  assert t['successor_block_id'] in B and int(t['successor_day_shift'])>0,'Transição inválida'
  assert B[b]['cycle_id']==B[t['successor_block_id']]['cycle_id'],'Transição entre ciclos'
  assert rfinite(B[b]),'Sessão inválida'
 # Valida fechamento de cada ciclo e período documentado pela cadeia de sucessores.
 cycle_summary={}
 for b in B:
  visited=set();curr=b;period=0
  while curr not in visited:
   visited.add(curr);period+=int(T[curr]['successor_day_shift']);curr=T[curr]['successor_block_id']
  assert curr==b,'Ciclo não retorna ao bloco inicial'
  cycle_summary[b]={'period_days':period,'blocks':len(visited)}
 summaries=[]
 for scen,nveh in SCENARIOS.items():
  dc=[0.]*N;events=[];vehicles=[];startblocks=sorted(B);adjustments=0
  for v in range(nveh):
   seed=startblocks[v%len(startblocks)];cycle=B[seed]['cycle_id'];period=cycle_summary[seed]['period_days']
   # Fase sintética declarada: distribuir deslocamentos ao longo do período, sem alterar transições.
   day=-(v//len(startblocks)+v%len(startblocks))%period-period
   block=seed;evcount=0;last_end=-float('inf');hops=0
   while day<365:
    r=B[block];s=float(r['charge_start_abs_min']);e=float(r['charge_end_abs_min']);ret=float(r['return_abs_min']);deadline=float(r['deadline_min']);energy=float(r['energy_dc_kwh']);power=float(r['power_dc_kw'])
    assert abs(power-POWER)<1e-7,'Potência diferente do contrato REV09'
    # Reancorar em dias civis: cada sessão mantém horário relativo ao dia do retorno.
    day_base=math.floor(ret/1440)*1440
    st=day*1440+(s-day_base);en=day*1440+(e-day_base);return_min=day*1440+(ret-day_base);dl=day*1440+(deadline-day_base)
    assert st>=return_min+10-1e-6 and en<=dl+1e-5,'Janela operacional inválida'
    # Reagendamento temporal controlado por veiculo.
    inicio_original = st
    st = max(st, last_end, return_min + 10)
    en = st + 60 * energy / power

    if en > dl + 1e-5:
     raise ValueError(
      f'INVIAVEL_REAGENDAMENTO scenario={scen} '
      f'vehicle={v+1} block={block} day={day} '
      f'delay_min={st-inicio_original:.6f} '
      f'end={en:.6f} deadline={dl:.6f}'
     )

    if st < last_end - 1e-6:
     raise AssertionError('Sobreposicao residual')

    if abs((en-st)*power/60-energy) > 1e-5:
     raise AssertionError('Energia DC nao conservada')

    if st > inicio_original + 1e-7:
     adjustments += 1

    last_end = en
    if en>0 and st<365*1440:
     covered=max(0,min(en,365*1440)-max(st,0))*power/60
     assert covered>=0
     first=max(0,math.floor(st/DT));last=min(N-1,math.ceil(en/DT)-1)
     for k in range(first,last+1):
      overlap=max(0,min(en,(k+1)*DT)-max(st,k*DT))
      dc[k]+=power*overlap/DT
     events.append({'scenario':scen,'vehicle_id':f'{scen}_BUS_{v+1:04d}','day_index':day,'block_id':block,'cycle_id':cycle,'successor_block_id':T[block]['successor_block_id'],'successor_day_shift':T[block]['successor_day_shift'],'return_min':round(return_min,6),'charge_start_min':round(st,6),'charge_end_min':round(en,6),'deadline_min':round(dl,6),'energy_dc_kwh_full':round(energy,6),'energy_dc_kwh_in_year':round(covered,6),'power_dc_kw':power,'charger_id_reference_only':r['charger_id']})
    day+=int(T[block]['successor_day_shift']);block=T[block]['successor_block_id'];hops+=1
    if hops>2000:raise RuntimeError('Cadeia excessiva')
   vehicles.append({'scenario':scen,'vehicle_id':f'{scen}_BUS_{v+1:04d}','seed_block_id':seed,'cycle_id':cycle,'phase_rule':'-(index//115 + index%115) modulo cycle_period - cycle_period','cycle_period_days':period,'events_in_year':sum(x['vehicle_id']==f'{scen}_BUS_{v+1:04d}' for x in events)})
  e_events=sum(x['energy_dc_kwh_in_year'] for x in events);e_grid=sum(dc)*.25
  assert abs(e_events-e_grid)<max(.05,e_grid*1e-8),(scen,e_events,e_grid)
  assert len(dc)==N and all(math.isfinite(x) and x>=0 for x in dc)
  dt0=datetime.datetime(a.ano,1,1)
  f,w=writer(out/f'D28_demanda_anual_{scen}_15min.csv',['scenario','interval_start_local','interval_end_local','interval_start_min','day_index','power_dc_kw','power_ac_kw','energy_dc_kwh','energy_ac_kwh'])
  with f:
   for k,power in enumerate(dc):
    st=dt0+datetime.timedelta(minutes=k*DT);en=st+datetime.timedelta(minutes=DT)
    w.writerow({'scenario':scen,'interval_start_local':st.isoformat(),'interval_end_local':en.isoformat(),'interval_start_min':k*DT,'day_index':k//96,'power_dc_kw':f'{power:.9f}','power_ac_kw':f'{power/ETA:.9f}','energy_dc_kwh':f'{power*.25:.9f}','energy_ac_kwh':f'{power*.25/ETA:.9f}'})
  f,w=writer(out/f'D28_eventos_anuais_{scen}.csv',list(events[0]))
  with f:w.writerows(events)
  f,w=writer(out/f'D28_veiculos_sinteticos_{scen}.csv',list(vehicles[0]))
  with f:w.writerows(vehicles)
  summaries.append({'reagendamentos':adjustments,'scenario':scen,'vehicles':nveh,'events':len(events),'intervals':N,'energy_dc_kwh':round(e_grid,4),'energy_ac_kwh':round(e_grid/ETA,4),'peak_ac_kw':round(max(dc)/ETA,4),'mean_ac_kwh_per_bus_day':round(e_grid/ETA/nveh/365,4),'peak_equivalent_138kw_chargers':round(max(dc)/POWER,3)})
 manifest={'status':'ANNUAL_SYNTHETIC_GENERATED_NOT_HOMOLOGATED','year_local':'2025 America/Sao_Paulo (UTC-03, no DST)','method':'documented block successor chains + explicitly synthetic vehicle allocation and phase staggering','assumptions':{'fleet_total_reference':450,'scenario_vehicles':SCENARIOS,'seed_assignment':'vehicle index modulo 115 documented blocks','phase_assignment':'deterministic vehicle-index phase; not empirically observed','calendar':'365 consecutive civil days, no differentiated weekdays/holidays','recarga':'138 kW DC fixed, 0.94 AC/DC efficiency, 10 min preparation','charging_infrastructure':'unlimited virtual chargers; charger_id in source is reference only','base_load':'not added; AC is charging-only','representativeness':'counterfactual synthetic, not real D28 operation','solar_alignment':'not performed'},'source_sha256':{src.name:sha(src),trans.name:sha(trans)},'summaries':summaries,'new_solver_executions':0,'scientific_release':'BLOCKED','solver_input_release':'PENDING_EXPLICIT_APPROVAL'}
 manifest['output_sha256']={x.name:sha(x) for x in out.glob('*.csv')}
 (out/'manifesto_anual.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf8')
 print(json.dumps({'status':manifest['status'],'summaries':summaries,'new_solver_executions':0,'scientific_release':'BLOCKED'},ensure_ascii=False))
def rfinite(r):
 try:return all(math.isfinite(float(r[k])) for k in ['return_abs_min','charge_start_abs_min','charge_end_abs_min','deadline_min','energy_dc_kwh','power_dc_kw'])
 except:return False
if __name__=='__main__':main()
