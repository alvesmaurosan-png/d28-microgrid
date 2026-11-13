"""Reconciliação REV08: somente leitura de fontes; não homologa nem executa MILP."""
import csv, hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main(root=ROOT):
 root=Path(root); evidence=root/'config/annual_f1_f2_evidence.json'; evidence.parent.mkdir(parents=True,exist_ok=True)
 sources={
 'temporal':['data/processed/annual_charging/manifesto_anual.json','data/processed/milp_inputs/R0_inputs_manifest.json','data/raw/solar/D28_solar_8760_modelo.csv'],
 'tariffs':['reports/D28_AVALIACAO_TARIFARIA_REV07.json','config/economics/r0_f1_exploratory_2026.json'],
 'pkm':['reports/D28_REV08_1C_F1_PKM_F3_AUDITORIA.json'],
 'economics':['data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx','reports/D28_ECONOMIA_DESPACHO_ANUAL_REV04.json','src/d28/economics/f1.py','src/d28/optimization/economic_dispatch_f1f2.py'],
 'r2':['src/d28/optimization/economic_dispatch_f1f2.py','scripts/05_piloto_economico_r0_r3.py'],
 'r3':['src/d28/optimization/economic_dispatch_f1f2.py','scripts/05_piloto_economico_r0_r3.py'],
 'auxiliaries':['data/processed/annual_charging/manifesto_anual.json','data/processed/milp_inputs/R0_inputs_manifest.json','src/d28/optimization/economic_dispatch_f1f2.py']}
 refs={k:[{'path':p,'sha256':sha(root/p)} for p in v if (root/p).is_file()] for k,v in sources.items()}
 observations=[]
 def obs(group,claim,result,detail):observations.append({'group':group,'check':claim,'result':result,'detail':detail})
 charging=root/sources['temporal'][0]; milp=root/sources['temporal'][1]
 a=read(charging) if charging.exists() else {}; m=read(milp) if milp.exists() else {}
 obs('temporal','manifestos_presentes','PASS' if a and m else 'BLOCKED','Manifestos anuais e MILP')
 obs('temporal','origem_homologada','BLOCKED' if 'NOT_HOMOLOGATED' in a.get('status','') else 'REVIEW',a.get('status','ausente'))
 obs('temporal','alinhamento_solar_mesmo_ano','BLOCKED' if 'not_same_observation_year' in m.get('alignment','') else 'REVIEW',m.get('alignment','ausente'))
 obs('temporal','mapeamento_dias_contrato','BLOCKED','Contrato exige source_day_for_calendar_day completo; não inferir a partir da posição')
 summary={x.get('scenario'):x for x in a.get('summaries',[])}
 for s in m.get('scenarios',[]):
  name=s.get('scenario'); t=summary.get(name,{}); n=s.get('intervals'); energy=s.get('charging_energy_ac_kwh'); ref=t.get('energy_ac_kwh')
  good=n==35040 and t.get('intervals')==35040 and isinstance(energy,(int,float)) and isinstance(ref,(int,float)) and math.isclose(energy,ref,rel_tol=1e-9,abs_tol=0.01)
  obs('temporal','integridade_'+str(name),'PASS' if good else 'BLOCKED',f'intervalos={n}; energia_MILP={energy}; energia_recarga={ref}')
  file=root/f'data/processed/milp_inputs/R0_inputs_{name}_15min.csv'
  if file.is_file():
   with file.open(encoding='utf-8-sig',newline='') as f:
    reader=csv.reader(f);head=next(reader,None);count=sum(1 for _ in reader)
   obs('temporal','arquivo_'+str(name),'PASS' if count==35040 else 'BLOCKED',f'linhas={count}; colunas={head}; sha256={sha(file)}')
  else:obs('temporal','arquivo_'+str(name),'BLOCKED','arquivo ausente')
 tariff=root/'reports/D28_AVALIACAO_TARIFARIA_REV07.json';t=read(tariff) if tariff.exists() else {}
 obs('tariffs','faturamento_contratual','BLOCKED' if 'CONTRACTUAL_NULL' in t.get('status','') else 'REVIEW',t.get('status','ausente'))
 econ=root/'reports/D28_ECONOMIA_DESPACHO_ANUAL_REV04.json';e=read(econ) if econ.exists() else {}
 obs('economics','reconciliacao_f1','BLOCKED' if 'NOT_HOMOLOGATED' in e.get('status','') else 'REVIEW',e.get('status','ausente'))
 pkm=root/'reports/D28_REV08_1C_F1_PKM_F3_AUDITORIA.json';p=read(pkm) if pkm.exists() else {}
 basis=p.get('pkm_basis',{})
 obs('pkm','pkm_servico_homologado','BLOCKED' if basis.get('blockers') else 'REVIEW',str(basis.get('blockers',[])))
 code=(root/'src/d28/optimization/economic_dispatch_f1f2.py').read_text(encoding='utf-8') if (root/'src/d28/optimization/economic_dispatch_f1f2.py').exists() else ''
 obs('r2','perdas_gas_sem_dupla_contagem','REVIEW' if 'DOUBLE_COUNT_R2_FUEL_AND_PRODUCTION' in code else 'BLOCKED','Proteção no código não comprova valores ou fronteiras anuais')
 obs('r3','cgob_regra_contabil','BLOCKED','Ausência de evidência independente de regra CGOB homologada')
 obs('auxiliaries','auxiliares_sem_dupla_contagem','BLOCKED','Carga AC de recarga sem base não veicular; custos auxiliares requerem conciliação')
 obs('economics','base_mestre_presente','PASS' if refs['economics'] and any(x['path'].endswith('.xlsx') for x in refs['economics']) else 'BLOCKED','Presença não equivale a aprovação dos parâmetros')
 old=read(evidence) if evidence.exists() else {}
 flags=['temporal_series_approved','energy_prices_approved','annual_pkm_approved','economic_parameters_approved','annual_cost_reconciliation_approved','r2_gas_loss_accounting_approved','r3_cgob_accounting_approved','auxiliary_no_double_count_approved']
 manifest={'revision':'REV08','status':'EVIDENCE_INDEXED_NOT_HOMOLOGATED','references':refs,'observations':observations}
 for key in flags:manifest[key]=old.get(key) is True  # preserva decisões anteriores; jamais promove por inferência
 evidence.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 out=root/'results/rev08_reconciliacao_unica.json';out.parent.mkdir(parents=True,exist_ok=True)
 report={'scientific_release':False,'documental_checks_ready':all(bool(refs[k]) for k in refs),'observations':observations,'evidence_manifest':str(evidence.relative_to(root))}
 out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print('REV08 EVIDENCE MANIFEST:',evidence)
 print('REV08 DOCUMENTAL:', 'READY' if report['documental_checks_ready'] else 'INCOMPLETE')
 print('REV08 SCIENTIFIC RELEASE: BLOCKED')
 print('REPORT:',out)
if __name__=='__main__':main()
