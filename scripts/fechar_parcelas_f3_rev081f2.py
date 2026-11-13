"""REV08.1f.2: evidence-linked, non-destructive F3 partial closure. No model changes."""
from __future__ import annotations
import hashlib, json, math
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'reports/D28_REV08_1F1_EVIDENCIAS_RECUPERADAS_F3.json'
ANNUAL=ROOT/'results/r0_annual_validation/annual_A_E100.json'
OUTPUT=ROOT/'reports/D28_REV08_1F2_PARCELAS_F3_COM_EVIDENCIAS.json'
FACTOR_BY_PARCEL={'PV_initial':'D11-003','BESS_initial':'D11-013','CHP_initial':'D11-007','biodigester':'D11-005','gasometer':'D11-006','grid_20y':'D11-017'}
UNITS={'PV_initial':('kWp','kgCO2e/kWp'),'BESS_initial':('kWh','kgCO2e/kWh de capacidade instalada'),'CHP_initial':('kWe','kgCO2e/kWe'),'biodigester':('t/ano','kgCO2e/(t/ano)'),'gasometer':('m³','kgCO2e/m³'),'grid_20y':('kWh','kgCO2e/kWh gerado (SIN histórico)')}
ACTIVITY_FIELDS={'PV_initial':('pv_kw','pv_capacity_kw'),'BESS_initial':('bess_kwh','bess_capacity_kwh'),'CHP_initial':('chp_kw','chp_capacity_kw'),'biodigester':('substrate_capacity_t_per_year',),'gasometer':('gasometer_m3',)}

def numeric(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0: return None
    return float(value)

def verified_annual(path):
    if not path.is_file():return None
    a=json.loads(path.read_text(encoding='utf-8-sig'))
    return a if a.get('status')=='OPTIMAL' and a.get('experiment')=='R0_ANNUAL_A_E100' else None

def find_activity(annual,parcel):
    if not annual:return None
    if parcel=='grid_20y':
        value=numeric(annual.get('grid_energy_kwh'))
        return None if value is None else {'value':value*20,'unit':'kWh','source':str(ANNUAL.relative_to(ROOT)),'field':'grid_energy_kwh','assumption':'20 years identical to validated R0 annual operation; conditional, no future evolution'}
    for field in ACTIVITY_FIELDS.get(parcel,()):
        value=numeric(annual.get(field))
        if value is not None:return {'value':value,'unit':UNITS[parcel][0],'source':str(ANNUAL.relative_to(ROOT)),'field':field}
    return None

def evaluate(data,annual):
    factors={f['id']:f for f in data['recovered_existing_factors']}
    calculations=[]; roots=[]
    for root in data['roots']:
        decisions=[]; cause=root['root_cause']; fid=FACTOR_BY_PARCEL.get(cause)
        for d in root['decisions']:
            arch=d['architecture']; ev=[]; missing=[]; status='PENDENTE'
            if fid:
                factor=factors.get(fid)
                if factor and numeric(factor.get('value')) is not None and factor.get('unit')==UNITS[cause][1]:
                    ev.append({'type':'factor','id':fid,'value':factor['value'],'unit':factor['unit'],'location':factor.get('location'),'provenance':factor.get('provenance'),'status':factor.get('status','NOT_HOMOLOGATED')})
                else:missing.append('fator '+fid+' com unidade compatível e origem')
                activity=find_activity(annual,cause) if arch=='R0' else None
                if activity:ev.append({'type':'activity',**activity})
                else:missing.append('atividade física verificada para '+arch+' / '+cause)
                if not missing:
                    val=ev[0]['value']*ev[1]['value']
                    calculations.append({'architecture':arch,'parcel':cause,'kgco2e':val,'conditional':True,'factor':ev[0],'activity':ev[1],'not_full_f3':True})
                    # Resolved means complete evidence of this cause only; not homologation of F3.
                    status='RESOLVIDA' if cause!='grid_20y' else 'PENDENTE'
                    if cause=='grid_20y':missing.append('homologação da hipótese de repetição anual por 20 anos')
            elif cause in ('MISSING_OR_UNVERIFIED:annual_pkm','PKM_SYNTHETIC_NOT_HOMOLOGATED'):
                missing.append('PKM anual homologado por cenário e horizonte; parâmetros D04 são sintéticos')
            elif cause in ('D11-014','D11-015','D11-016','D11-018','D11-019'):
                f=factors.get(cause)
                if f and numeric(f.get('value')) is not None and f.get('unit'):
                    ev.append({'type':'factor','id':cause,**f})
                    status='RESOLVIDA'
                else:missing.append('fator '+cause+' numérico com unidade, fonte e aplicabilidade')
            else:
                missing.append('inventário/atividade e fronteira completos demonstrados para '+arch+' / '+cause)
            decisions.append({'architecture':arch,'status':status,'evidence':ev,'missing_exactly':missing})
        roots.append({**{k:v for k,v in root.items() if k!='decisions'},'root_status':'RESOLVIDA' if all(d['status']=='RESOLVIDA' for d in decisions) else 'PENDENTE','decisions':decisions})
    # R0 asset inventory is not a root in the original 23-cause list; compute separately if annual design explicitly contains capacity.
    for parcel in ('PV_initial','BESS_initial','grid_20y'):
        activity=find_activity(annual,parcel)
        fid=FACTOR_BY_PARCEL[parcel]; factor=factors.get(fid)
        if activity and factor and numeric(factor.get('value')) is not None and factor.get('unit')==UNITS[parcel][1]:
            calculations.append({'architecture':'R0','parcel':parcel,'kgco2e':activity['value']*factor['value'],'conditional':True,'factor':{'id':fid,**factor},'activity':activity,'not_full_f3':True,'root_resolution':'NOT_IN_ORIGINAL_R0_ROOTS'})
    return {'revision':'REV08.1f.2','input_roots':len(roots),'original_records':sum(r['occurrences'] for r in roots),'root_status_counts':dict(Counter(r['root_status'] for r in roots)),'architecture_status_counts':{a:dict(Counter(d['status'] for r in roots for d in r['decisions'] if d['architecture']==a)) for a in ('R0','R1','R2','R3')},'partial_calculations':calculations,'roots':roots,'f3_complete':False,'pareto_eligible':False,'r3_policy':'NATURAL_GAS_PHYSICAL_CGOB_ACCOUNTING_ONLY_NO_AUTO_DEDUCTION','physical_models_modified':False,'economic_models_modified':False,'note':'Partial computations are conditional, not homologated. No R0 annual results are applied to R1-R3. No missing values are zero-filled.'}

def main():
    if not INPUT.is_file():raise SystemExit('Arquivo necessário ausente: '+str(INPUT))
    data=json.loads(INPUT.read_text(encoding='utf-8-sig'))
    annual=verified_annual(ANNUAL)
    out=evaluate(data,annual)
    if out['input_roots']!=23 or out['original_records']!=57:raise ValueError('Baseline incompatible: expected 23 roots and 57 records')
    out['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (INPUT,ANNUAL) if p.is_file()}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('REV08.1f.2 | causas:',out['root_status_counts'],'| parcelas calculadas:',len(out['partial_calculations']))
    for p in out['partial_calculations']:print(p['architecture'],p['parcel'],round(p['kgco2e'],3),'kgCO2e (condicional)')
    print('F3 completo: False | relatório:',OUTPUT)

if __name__=='__main__':main()
