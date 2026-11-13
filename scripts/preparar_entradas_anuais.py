#!/usr/bin/env python3
"""Extrai e concilia registros documentados; NÃO fabrica calendário anual ou roda solver."""
import argparse,csv,hashlib,json,datetime
from pathlib import Path
from openpyxl import load_workbook

def records(path,sheet):
    wb=load_workbook(path,read_only=True,data_only=True)
    if sheet not in wb.sheetnames: raise ValueError(f'Aba ausente: {sheet}')
    it=wb[sheet].values
    headers=[str(x).strip() if x is not None else '' for x in next(it)]
    return [{h:v for h,v in zip(headers,row)} for row in it if any(x is not None for x in row)]
def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write(path,rows):
    if not rows:return
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--logistica',required=True);ap.add_argument('--programacao',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();lp=Path(a.logistica);pp=Path(a.programacao);out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise SystemExit('Saída não vazia: escolha pasta nova, sem sobrescrever')
    out.mkdir(parents=True,exist_ok=True)
    l=records(lp,'Sessoes');p=records(pp,'PROGRAMACAO_115');s=records(pp,'SESSOES_ENERGIA')
    def index(rows):
        d={}
        for r in rows:
            k=str(r['block_id'])
            if k in d:raise ValueError('block_id duplicado: '+k)
            d[k]=r
        return d
    li,pi,si=map(index,(l,p,s));keys=set(li)|set(pi)|set(si)
    issues=[];joined=[]
    for k in sorted(keys):
        if k not in li or k not in pi or k not in si:
            issues.append({'block_id':k,'issue':'MISSING_IN_ONE_SOURCE'});continue
        x,y,z=li[k],pi[k],si[k]
        for name in ('successor_block_id',):
            if str(x.get(name))!=str(y.get(name)) or str(x.get(name))!=str(z.get(name)):
                issues.append({'block_id':k,'issue':'SUCCESSOR_MISMATCH'})
        energy=float(x['energy_kwh']);ep=float(y['charge_energy_kwh'])
        if abs(energy-ep)>0.001:issues.append({'block_id':k,'issue':'ENERGY_MISMATCH'})
        start=float(y['charge_start_abs_min']);end=float(y['charge_end_abs_min']);ret=float(x['return_abs_min']);deadline=float(x['departure_next_abs_min'])
        if start<ret+10-0.001:issues.append({'block_id':k,'issue':'PREPARATION_10MIN_VIOLATION'})
        if end>deadline+0.001:issues.append({'block_id':k,'issue':'DEADLINE_VIOLATION'})
        if abs((end-start)*float(y['charge_power_dc_kw'])/60-ep)>0.01:issues.append({'block_id':k,'issue':'ENERGY_POWER_DURATION_MISMATCH'})
        joined.append({'block_id':k,'vehicle_id_representative':x['vehicle_id_representative'],'cycle_id':x['cycle_id'],'successor_block_id':x['successor_block_id'],'charger_id':y['charger_id'],'return_abs_min':ret,'earliest_charge_min':ret+10,'charge_start_abs_min':start,'charge_end_abs_min':end,'deadline_min':deadline,'energy_dc_kwh':ep,'power_dc_kw':y['charge_power_dc_kw'],'status_original':y['status']})
    write(out/'sessoes_conciliadas_115.csv',joined);write(out/'inconsistencias.csv',issues)
    cycles=records(lp,'Ciclos');write(out/'ciclos_documentados.csv',cycles)
    summary={'status':'SOURCE_RECONCILIATION_ONLY','source_files':{lp.name:digest(lp),pp.name:digest(pp)},'logistica_rows':len(l),'programacao_rows':len(p),'energia_rows':len(s),'joined_rows':len(joined),'issues':len(issues),'cycles':len(cycles),'scenarios_requested':['E100','E200','E300','E375','E450'],'annual_intervals_per_scenario_target':35040,'annual_intervals_generated':0,'annual_blockers':['Não há correspondência documentada das 115 sessões aos cinco cenários','Não há calendário operacional de 365 dias vinculado aos ciclos','Veículos representativos não equivalem necessariamente a ônibus individuais','Eficiência 0,94 pertence ao gerador REV09, não está certificada nesta programação'],'new_solver_executions':0,'scientific_release':'BLOCKED'}
    (out/'relatorio.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
