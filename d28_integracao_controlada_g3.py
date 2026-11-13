#!/usr/bin/env python3
"""D28 G3: integração controlada F1/F2, cache persistente, no máximo 2 novos MILPs.
Executar na raiz do repositório, ao lado de rodar_d28_rev16_1.py.
Não executa NSGA-II e não modifica o MILP.
"""
import argparse, csv, hashlib, json, math, subprocess, sys, tempfile, shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/processed/milp_inputs/R0_inputs_E100_15min.csv'
ECON=ROOT/'config/economics/r0_f1_exploratory_2026.json'
RUNNER=ROOT/'rodar_d28_rev16_1.py'
RESULT=ROOT/'results/D28_REV16_1_R0_E100_ANUAL.json'
GRID=ROOT/'results/D28_REV16_1_R0_E100_GRID_15MIN.csv'
CACHE=ROOT/'results/D28_G3_CACHE.json'
OUT=ROOT/'results/D28_G3_INTEGRACAO_CONTROLADA.json'
PKM=137675700.0
DESIGNS=[{'pv_kw':1908.225,'bess_kwh':15000.,'pcs_kw':5500.},
         {'pv_kw':1908.225,'bess_kwh':20000.,'pcs_kw':5500.},
         {'pv_kw':1908.225,'bess_kwh':30000.,'pcs_kw':5500.}]

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as f:
        json.dump(obj,f,indent=2,ensure_ascii=False)
        tmp=Path(f.name)
    tmp.replace(path)

def key(design,source):
    payload={'design':design,'annual_pkm':PKM,'source':source,'scenario':'R0/E100',
             'tariff_mode':'energy_plus_monthly_demand','c_rate':0.55}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(report,design,source):
    if report.get('status')!='PASS':return False,'status não PASS'
    if report.get('f3_excluded') is not True:return False,'F3 não explicitamente excluída'
    got=report.get('design') or {}
    for k,v in design.items():
        if not math.isclose(float(got.get(k,float('nan'))),v,rel_tol=1e-10,abs_tol=1e-7):return False,f'design.{k} diferente'
    if not math.isclose(float(report.get('annual_pkm',float('nan'))),PKM,rel_tol=1e-12):return False,'PKM diferente'
    provenance=report.get('provenance') or {}
    if provenance.get('series_sha256')!=source['series_sha256'] or provenance.get('economics_sha256')!=source['economics_sha256']:
        return False,'proveniência de entradas diferente'
    for k in ('f1_brl_per_pkm','f2_kw','solver_objective_brl','annual_energy_total_brl'):
        if not math.isfinite(float(report.get(k,float('nan')))):return False,f'{k} ausente'
    if abs(float(report['solver_objective_brl'])-float(report['annual_energy_total_brl']))>0.01:return False,'objetivo solver != conta anual'
    return True,'validado'

def pareto(rows):
    ok=[r for r in rows if r['status']=='PASS']
    return [r for r in ok if not any(s is not r and s['f1_brl_per_pkm']<=r['f1_brl_per_pkm'] and s['f2_kw']<=r['f2_kw'] and (s['f1_brl_per_pkm']<r['f1_brl_per_pkm'] or s['f2_kw']<r['f2_kw']) for s in ok)]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--max-new-solves',type=int,default=2)
    p.add_argument('--timeout-seconds',type=int,default=3600)
    a=p.parse_args()
    if a.max_new_solves<0 or a.max_new_solves>2:p.error('O piloto permite de 0 a 2 novas resoluções')
    for f in (DATA,ECON,RUNNER):
        if not f.is_file():raise SystemExit(f'Arquivo necessário ausente: {f}')
    source={'series_sha256':digest(DATA),'economics_sha256':digest(ECON),
            'runner_sha256':digest(RUNNER)}
    store=json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {'entries':{}}
    entries=store.get('entries',{})
    # Importar somente resultado G2 comprovadamente compatível; nunca confiar só em F1/F2.
    if RESULT.exists():
        previous=json.loads(RESULT.read_text(encoding='utf-8'))
        valid,why=validate(previous,DESIGNS[0],source)
        if valid:
            k=key(DESIGNS[0],source)
            entries.setdefault(k,{'report':previous,'source':'G2_EXISTING_VALIDATED'})
            print('G2 EXISTENTE: importado para cache, sem resolver MILP',flush=True)
        else:print('G2 EXISTENTE: não reutilizado:',why,flush=True)
    rows=[];new_solves=0
    for i,design in enumerate(DESIGNS,1):
        k=key(design,source)
        entry=entries.get(k)
        if entry:
            valid,why=validate(entry['report'],design,source)
            if not valid:
                print(f'CACHE inválido candidato {i}: {why}',flush=True)
                entry=None
        if entry:
            report=entry['report'];mode='CACHE'
        elif new_solves>=a.max_new_solves:
            rows.append({'candidate':i,'design':design,'status':'NOT_EVALUATED_BUDGET','source':'BUDGET'})
            print(f'CANDIDATO {i}: não avaliado (orçamento esgotado)',flush=True)
            continue
        else:
            # Preservar saídas G2 existentes: o runner sobrescreve nomes fixos.
            archive=ROOT/'results/G3_preserved';archive.mkdir(parents=True,exist_ok=True)
            stamp=f'candidate_{i:02d}'
            for f in (RESULT,GRID):
                if f.exists():shutil.copy2(f,archive/f'{stamp}_PRE_{f.name}')
            cmd=[sys.executable,str(RUNNER),'--pv-kw',str(design['pv_kw']),
                 '--bess-kwh',str(design['bess_kwh']),'--pcs-kw',str(design['pcs_kw']),
                 '--annual-pkm',str(int(PKM))]
            new_solves+=1
            print(f'CANDIDATO {i}: MILP real {new_solves}/{a.max_new_solves}',flush=True)
            try:
                proc=subprocess.run(cmd,cwd=ROOT,timeout=a.timeout_seconds,check=False)
                if proc.returncode or not RESULT.exists():raise RuntimeError(f'runner retornou {proc.returncode}')
                report=json.loads(RESULT.read_text(encoding='utf-8'))
                valid,why=validate(report,design,source)
                if not valid:raise RuntimeError(f'validação falhou: {why}')
                for f in (RESULT,GRID):
                    if f.exists():shutil.copy2(f,archive/f'{stamp}_{f.name}')
                entries[k]={'report':report,'source':'G3_NEW_SOLVE'}
                atomic_json(CACHE,{'entries':entries,'note':'Chave inclui design, PKM, hashes de entradas e runner'})
                mode='MILP_REAL'
            except Exception as exc:
                rows.append({'candidate':i,'design':design,'status':'FAILED','error':str(exc)})
                atomic_json(OUT,{'status':'INCOMPLETE','objectives':['F1','F2'],'new_solves':new_solves,'rows':rows})
                raise
        rows.append({'candidate':i,'design':design,'status':'PASS','source':mode,
                     'f1_brl_per_pkm':report['f1_brl_per_pkm'],'f2_kw':report['f2_kw'],
                     'annual_energy_total_brl':report['annual_energy_total_brl'],
                     'solver_objective_brl':report['solver_objective_brl']})
        print(f"CANDIDATO {i}: {mode} | F1={report['f1_brl_per_pkm']:.9f} | F2={report['f2_kw']:.3f}",flush=True)
    front=pareto(rows)
    result={'status':'PASS' if len(rows)==3 and all(r['status']=='PASS' for r in rows) else 'INCOMPLETE',
            'classification':'INTEGRATION_SMOKE_TEST_NOT_PARETO_CONVERGENCE',
            'objectives':['F1_BRL_PER_PKM','F2_PCC_PEAK_KW'],'f3_excluded':True,
            'source':source,'new_solves':new_solves,'max_new_solves':a.max_new_solves,
            'rows':rows,'nondominated_sample':[r['candidate'] for r in front],
            'warning':'Amostra de três designs não é NSGA-II nem valida suficiência do domínio BESS.'}
    atomic_json(OUT,result)
    print('RELATORIO:',OUT,flush=True)
    print('NOVOS MILPs:',new_solves,flush=True)

if __name__=='__main__':main()
