"""REV08.1f.3: R0 ACV inventory closure audit; no physical/economic model modifications."""
from __future__ import annotations
import json, math, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/D28_REV08_1F1_EVIDENCIAS_RECUPERADAS_F3.json'
PREVIOUS=ROOT/'reports/D28_REV08_1F2_PARCELAS_F3_COM_EVIDENCIAS.json'
OUT=ROOT/'reports/D28_REV08_1F3_FRONTEIRA_ACV_R0.json'

# Environmental-factor values must have their own explicit source and unit.
REQUIRED={
 'PCS_fabricacao':('D11-014','potencia_PCS_kW','kgCO2e/kW'),
 'carregadores_fabricacao':('D11-014','quantidade_carregadores','kgCO2e/unidade'),
 'inversores_PV_fabricacao':('D11-019','potencia_inversores_kW','kgCO2e/kW'),
 'fim_vida_PV':('D11-018','potencia_PV_kWp','kgCO2e/kWp'),
 'fim_vida_BESS':('D11-018','capacidade_BESS_kWh','kgCO2e/kWh'),
 'fim_vida_PCS':('D11-018','potencia_PCS_kW','kgCO2e/kW'),
 'fim_vida_carregadores':('D11-018','quantidade_carregadores','kgCO2e/unidade'),
 'fim_vida_inversores':('D11-018','potencia_inversores_kW','kgCO2e/kW'),
 'reposicao_BESS':('D11-004','capacidade_BESS_kWh','kgCO2e/kWh'),
}

def number(x):
 return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>=0

def audit(data,previous,additional=None):
 additional=additional or {}
 factors={x['id']:x for x in data.get('recovered_existing_factors',[])}
 prior={x['parcel']:x for x in previous.get('partial_calculations',[]) if x.get('architecture')=='R0'}
 parcels=[]
 for name in ('PV_initial','BESS_initial','grid_20y'):
  if name in prior:
   p=prior[name]
   parcels.append({'parcel':name,'status':'CALCULADA_CONDICIONAL','kgco2e':p['kgco2e'],'factor':p['factor'],'activity':p['activity'],'source':'REV08.1f.2','included_in_partial_subtotal':True})
  else:parcels.append({'parcel':name,'status':'PENDENTE','missing':['parcela anterior não demonstrada em REV08.1f.2'],'included_in_partial_subtotal':False})
 for name,(fid,activity_key,unit) in REQUIRED.items():
  # Explicit user-provided factors can only be used when fully sourced and unit-matched.
  factor=additional.get('factors',{}).get(name)
  activity=additional.get('activities',{}).get(activity_key)
  missing=[]
  if not (isinstance(factor,dict) and number(factor.get('value')) and factor.get('unit')==unit and factor.get('source') and factor.get('status')):
   missing.append(f'fator ambiental {fid} específico para {name}, unidade {unit}, fonte e status')
  if not (isinstance(activity,dict) and number(activity.get('value')) and activity.get('unit')==activity_key.split('_')[-1] and activity.get('source')):
   missing.append(f'atividade {activity_key} com unidade e fonte')
  if name=='reposicao_BESS':
   # D11-004 is labelled legacy; it is NOT interchangeable with D11-013.
   if not additional.get('replacement_schedule_verified'):
    missing.append('confirmar reposição física BESS no ano 12 (D07-016), quantidade e fronteira de fabricação da reposição')
  if missing:
   parcels.append({'parcel':name,'status':'PENDENTE','missing':missing,'existing_master_factor':fid,'note':'Não usar fator genérico ou legado sem comprovar fronteira e unidade','included_in_partial_subtotal':False})
  else:
   multiplier=1
   if name=='reposicao_BESS': multiplier=additional.get('replacement_units',1)
   if not number(multiplier):raise ValueError('replacement_units inválido')
   parcels.append({'parcel':name,'status':'CALCULADA_CONDICIONAL','kgco2e':factor['value']*activity['value']*multiplier,'factor':factor,'activity':activity,'included_in_partial_subtotal':True})
 # No automatic closure of non-overlap: this requires an explicit documented coverage matrix.
 checks={
  'fabricacao_PV_BESS':all(x['status']=='CALCULADA_CONDICIONAL' for x in parcels if x['parcel'] in ('PV_initial','BESS_initial')),
  'eletricidade_rede_20y_condicional':any(x['parcel']=='grid_20y' and x['status']=='CALCULADA_CONDICIONAL' for x in parcels),
  'PCS_carregadores_inversores':all(x['status']=='CALCULADA_CONDICIONAL' for x in parcels if x['parcel'] in ('PCS_fabricacao','carregadores_fabricacao','inversores_PV_fabricacao')),
  'reposicoes':all(x['status']=='CALCULADA_CONDICIONAL' for x in parcels if x['parcel']=='reposicao_BESS'),
  'fim_de_vida':all(x['status']=='CALCULADA_CONDICIONAL' for x in parcels if x['parcel'].startswith('fim_vida_')),
  'inventario_sem_sobreposicao_documentado':additional.get('nonoverlap_verified') is True,
  'PKM_homologado':additional.get('pkm_homologado') is True,
  'fatores_homologados':additional.get('fatores_homologados') is True,
  'projecao_20y_homologada':additional.get('projecao_20y_homologada') is True,
 }
 subtotal=sum(x['kgco2e'] for x in parcels if x['status']=='CALCULADA_CONDICIONAL')
 complete=all(checks.values()) and all(x['status']=='CALCULADA_CONDICIONAL' for x in parcels)
 return {'revision':'REV08.1f.3','architecture':'R0','partial_subtotal_kgco2e':subtotal,'partial_subtotal_is_not_F3':True,'parcels':parcels,'boundary_checks':checks,'missing_boundary_checks':[k for k,v in checks.items() if not v], 'f3_r0_complete':complete,'pareto_eligible':False,'physical_models_modified':False,'economic_models_modified':False,'note':'Fatores D11-014/018/019 não preenchidos artificialmente; D11-004 legado não equiparado à fabricação inicial; valores existentes não homologados.'}

def main():
 if not BASE.exists() or not PREVIOUS.exists():raise SystemExit('Relatórios REV08.1f.1 e REV08.1f.2 necessários em reports/')
 data=json.loads(BASE.read_text(encoding='utf-8-sig'));prev=json.loads(PREVIOUS.read_text(encoding='utf-8-sig'))
 # Optional evidence must be explicitly authored and sourced; never create automatically.
 opt=ROOT/'config/f3_r0_evidencias_adicionais.json'
 additional=json.loads(opt.read_text(encoding='utf-8-sig')) if opt.exists() else None
 out=audit(data,prev,additional)
 out['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE,PREVIOUS,opt) if p.exists()}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('REV08.1f.3 | R0 parcelas calculadas:',sum(p['status']=='CALCULADA_CONDICIONAL' for p in out['parcels']),'/',len(out['parcels']))
 print('Subtotal condicional:',round(out['partial_subtotal_kgco2e'],3),'kgCO2e | F3 completo:',out['f3_r0_complete'])
 print('Fronteiras pendentes:',out['missing_boundary_checks']);print('Relatório:',OUT)
if __name__=='__main__':main()
