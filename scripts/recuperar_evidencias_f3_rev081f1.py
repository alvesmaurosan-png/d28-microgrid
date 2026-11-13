"""REV08.1f.1: recover existing F3 evidence; never infer missing LCA factors or activities."""
from __future__ import annotations
import hashlib, json, math, re
from pathlib import Path
from collections import Counter
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
PREV=ROOT/'reports/D28_REV08_1F_RESOLUCAO_CAUSAS_F3.json'
MASTER=ROOT/'data/raw/parametros/Base_Mestre_D28_PC_REV07_REV02.xlsx'
ANNUAL=ROOT/'results/r0_annual_validation/annual_A_E100.json'
OUT=ROOT/'reports/D28_REV08_1F1_EVIDENCIAS_RECUPERADAS_F3.json'
D11_IDS={'D11-003','D11-005','D11-006','D11-007','D11-008','D11-009','D11-010','D11-013','D11-014','D11-015','D11-016','D11-017','D11-018','D11-019'}
# These activity fields exist in the R0 annual dispatch evidence or in its validated design.
R0_DESIGN={'PV_initial':('pv_kw','kWp'),'BESS_initial':('bess_kwh','kWh')}
R0_DESIGN_FALLBACK={'pv_kw':205.4806088017267,'bess_kwh':28272.75736597176,'pcs_kw':4996.651562474392}

def number(x):
    if isinstance(x,bool) or x is None:return None
    if isinstance(x,(int,float)):
        return float(x) if math.isfinite(x) else None
    s=str(x).strip().replace(',','.')
    try:
        n=float(s)
        return n if math.isfinite(n) else None
    except ValueError:pass
    # Only accept number + explicit unit (not a free-text estimate or formula).
    m=re.fullmatch(r'\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s+(kgCO2e/kWh(?:\s+de\s+capacidade\s+instalada)?|kgCO2e/kWp|kgCO2e/kWe|kgCO2e/m³|kgCO2e/\(t/ano\)|kgCO2e/kWh\s+gerado\s*\(SIN\s+histórico\))\s*',s,re.I)
    return float(m.group(1)) if m else None

def master_rows(path):
    wb=load_workbook(path,read_only=True,data_only=True)
    try:
        sheet=wb['Parametros_137']; rows=iter(sheet.values); next(rows)
        return {str(r[0]):{'value':number(r[3]),'raw':str(r[3]) if r[3] is not None else None,'unit':r[4], 'name':r[2], 'source':r[5], 'cell':f'{sheet.title}!D{i}'} for i,r in enumerate(rows,2) if r[0]}
    finally:wb.close()

def read_annual(path):
    if not path.exists():return None
    a=json.loads(path.read_text(encoding='utf-8'))
    if a.get('status')!='OPTIMAL' or a.get('experiment')!='R0_ANNUAL_A_E100':return None
    return a

def evidence(arch,cause,category,rows,annual):
    """Return verified evidence for an *existing* root, not a replacement for the LCA gate."""
    if category=='FATORES_DE_EMISSAO':
        r=rows.get(cause)
        if r and r['value'] is not None and r['value']>=0 and r['unit']:
            return [{'source':'Base_Mestre','id':cause,'location':r['cell'],'value':r['value'],'unit':r['unit'],'provenance':r['source'],'verification':'NUMERIC_NOT_HOMOLOGATED'}]
        return []
    if category=='DADOS_DE_ATIVIDADE' and arch=='R0' and annual:
        if cause=='grid_20y':
            n=number(annual.get('grid_energy_kwh'))
            if n is not None and n>=0:
                return [{'source':'R0_ANNUAL_A_E100','field':'grid_energy_kwh','value':n,'unit':'kWh/year','verification':'VALIDATED_ANNUAL_R0_ONLY'}]
        if cause in R0_DESIGN:
            field,unit=R0_DESIGN[cause]
            # The R0 design is embedded as a constant in REV08.1d, not in the annual result.
            # Recover as conditional evidence, do not claim it as a separately verified dispatch field.
            return [{'source':'REV08.1d_R0_DESIGN','field':field,'value':R0_DESIGN_FALLBACK[field],'unit':unit,'verification':'CONDITIONAL_DESIGN_FROM_PRIOR_AUDIT'}]
    return []

def resolve(previous,rows,annual):
    results=[]
    for root in previous['roots']:
        decisions=[]
        for d in root['decisions']:
            arch=d['architecture']; cat=root['category']; cause=root['root_cause']
            ev=evidence(arch,cause,cat,rows,annual)
            # Only evidence that matches the exact original cause can resolve it.
            status='RESOLVIDA' if ev else 'PENDENTE'
            decisions.append({'architecture':arch,'status':status,'evidence':ev,'note':('Evidência recuperada; não implica F3 completo nem homologação' if ev else 'Evidência indispensável não localizada ou não suficiente')})
        root_status='RESOLVIDA' if all(d['status']=='RESOLVIDA' for d in decisions) else 'PENDENTE'
        results.append({'category':root['category'],'root_cause':root['root_cause'],'occurrences':root['occurrences'],'root_status':root_status,'decisions':decisions})
    if len(results)!=23 or sum(x['occurrences'] for x in results)!=57:raise ValueError('REV08.1f baseline inconsistent (expected 23 roots / 57 occurrences)')
    counts=dict(Counter(r['root_status'] for r in results))
    per_arch={a:dict(Counter(d['status'] for r in results for d in r['decisions'] if d['architecture']==a)) for a in ('R0','R1','R2','R3')}
    return {'revision':'REV08.1f.1','source':'REV08.1f + Base Mestre + validated annual R0 (if available)', 'root_status_counts':counts,'architecture_decision_counts':per_arch,'original_records':57,'root_causes':23,'roots':results,'f3_complete':False,'r3_policy':'NATURAL_GAS_PHYSICAL_CGOB_ACCOUNTING_ONLY_NO_AUTO_DEDUCTION','physical_models_modified':False,'economic_models_modified':False,'warning':'Existing factor/activity evidence is not a completed lifecycle inventory; missing inputs are never zero-filled.'}

def main():
    if not PREV.is_file() or not MASTER.is_file():raise SystemExit('Required: REV08.1f report and Base Mestre. Missing: '+', '.join(str(p) for p in (PREV,MASTER) if not p.is_file()))
    prev=json.loads(PREV.read_text(encoding='utf-8'))
    rows=master_rows(MASTER); annual=read_annual(ANNUAL)
    result=resolve(prev,rows,annual)
    result['recovered_existing_factors']=[{'id':k,'value':v['value'],'unit':v['unit'],'location':v['cell'],'provenance':v['source'],'status':'PRESENT_NOT_HOMOLOGATED'} for k,v in sorted(rows.items()) if k in D11_IDS and v['value'] is not None and v['unit']]
    result['recovered_operational_parameters']=[{'id':k,'value':v['value'],'unit':v['unit'],'location':v['cell']} for k,v in sorted(rows.items()) if k.startswith(('D08-','D09-','D04-')) and v['value'] is not None and v['unit']]
    result['recoverable_but_not_blocker_closing']='Available parameters are not substitutes for absent annual R1/R2/R3 dispatch or missing D11-014/015/016/018/019.'
    result['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (PREV,MASTER) if p.is_file()}
    if annual:result['source_sha256'][ANNUAL.name]=hashlib.sha256(ANNUAL.read_bytes()).hexdigest()
    result['annual_R0_available']=annual is not None
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('REV08.1f.1 | causas:',result['root_status_counts'],'| anual R0:',result['annual_R0_available'])
    for a,c in result['architecture_decision_counts'].items():print(a,c)
    print('F3 completo: False | relatório:',OUT)

if __name__=='__main__':main()
