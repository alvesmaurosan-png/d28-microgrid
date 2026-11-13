#!/usr/bin/env python3
"""Piloto do controlador BESS adaptativo; modo mock nao executa MILP.
Modo real: invoca o script REV16.1 existente, sem editar modulos do modelo.
"""
import argparse, json, math, subprocess, sys
from pathlib import Path


def nondominated(rows):
    valid=[r for r in rows if r.get('status')=='PASS' and all(math.isfinite(float(r[k])) for k in ('f1_brl_per_pkm','f2_kw'))]
    return [r for i,r in enumerate(valid) if not any(j!=i and s['f1_brl_per_pkm']<=r['f1_brl_per_pkm'] and s['f2_kw']<=r['f2_kw'] and (s['f1_brl_per_pkm']<r['f1_brl_per_pkm'] or s['f2_kw']<r['f2_kw']) for j,s in enumerate(valid))]


def mock_stage(bound, stage):
    # Problema sintético: melhorias de F2 até 24 MWh; após isso custos crescem.
    rows=[]
    for k in range(21):
        e=bound*k/20
        rows.append({'status':'PASS','design':{'pv_kw':1200.,'bess_kwh':e,'pcs_kw':min(5500.,.55*e)},
                     'f1_brl_per_pkm':.075 + .0000012*e + .00000000003*e*e,
                     'f2_kw':2500-650*(1-math.exp(-min(e,24000)/7500))})
    return rows


def real_stage(bound, stage, args):
    script=Path(args.runner).resolve()
    if not script.is_file(): raise FileNotFoundError(script)
    result=script.parent/'results'/'D28_REV16_1_R0_E100_NSGA2.json'
    cmd=[sys.executable,str(script),'--nsga2','--annual-pkm',str(args.annual_pkm),
         '--bess-max-kwh',str(bound),'--population',str(args.population),
         '--generations',str(args.generations)]
    proc=subprocess.run(cmd,cwd=script.parent,check=False)
    if proc.returncode: raise RuntimeError(f'NSGA-II terminou com codigo {proc.returncode}')
    raw=json.loads(result.read_text(encoding='utf-8'))
    rows=[]
    for r in raw.get('evaluations',[]):
        if r.get('status')=='PASS' and r.get('f1_brl_per_pkm') is not None:
            rows.append(r)
    return rows


def main():
    p=argparse.ArgumentParser(description='Controlador de dominio BESS adaptativo D28')
    p.add_argument('--mode',choices=['mock','real'],default='mock')
    p.add_argument('--initial-kwh',type=float,default=20000)
    p.add_argument('--max-stages',type=int,default=3)
    p.add_argument('--expansion-factor',type=float,default=2.)
    p.add_argument('--boundary-fraction',type=float,default=.05)
    p.add_argument('--boundary-min-share',type=float,default=.05)
    p.add_argument('--runner',default='rodar_d28_rev16_1.py')
    p.add_argument('--annual-pkm',type=float,default=137675700)
    p.add_argument('--population',type=int,default=8)
    p.add_argument('--generations',type=int,default=2)
    p.add_argument('--output',default='D28_BESS_ADAPTATIVO_PILOTO.json')
    a=p.parse_args()
    if not math.isfinite(a.initial_kwh) or a.initial_kwh<=0 or a.max_stages<1 or a.expansion_factor<=1: p.error('Dominio ou expansao invalidos')
    if not 0<a.boundary_fraction<1 or not 0<a.boundary_min_share<=1: p.error('Criterios de borda invalidos')
    if a.mode=='real' and a.annual_pkm<=0: p.error('PKM invalido')
    bound=a.initial_kwh; stages=[]
    for stage in range(1,a.max_stages+1):
        rows=mock_stage(bound,stage) if a.mode=='mock' else real_stage(bound,stage,a)
        front=nondominated(rows)
        boundary=[r for r in front if r['design']['bess_kwh']>=bound*(1-a.boundary_fraction)]
        share=len(boundary)/len(front) if front else 0
        expand=bool(front) and share>=a.boundary_min_share and stage<a.max_stages
        reason=('NO_FEASIBLE_FRONT' if not front else 'BOUNDARY_OCCUPIED' if expand else
                'MAX_STAGES_REACHED' if share>=a.boundary_min_share else 'BOUNDARY_NOT_OCCUPIED')
        item={'stage':stage,'bess_max_kwh':bound,'feasible_evaluations':len(rows),'pareto_count':len(front),
              'boundary_pareto_count':len(boundary),'boundary_share':share,
              'expand':expand,'reason':reason,
              'pareto':[{'bess_kwh':r['design']['bess_kwh'],'f1':r['f1_brl_per_pkm'],'f2':r['f2_kw']} for r in front]}
        stages.append(item)
        print(f'ETAPA {stage} | BESS_MAX={bound:.1f} kWh | factiveis={len(rows)} | Pareto={len(front)} | borda={share:.1%} | {reason}',flush=True)
        if not expand:break
        bound*=a.expansion_factor
    report={'mode':a.mode,'classification':'EXPLORATORY_NOT_HOMOLOGATED','f3_excluded':True,
            'objectives':['F1_BRL_PER_PKM','F2_PCC_PEAK_KW'],'stages':stages,
            'warning':'O teste mock verifica apenas a logica do controlador; nao valida MILP nem convergencia NSGA-II.' if a.mode=='mock' else
            'NSGA-II heuristico: ausencia de solucoes na borda nao prova otimalidade global.'}
    Path(a.output).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('RELATORIO:',Path(a.output).resolve())

if __name__=='__main__':main()
