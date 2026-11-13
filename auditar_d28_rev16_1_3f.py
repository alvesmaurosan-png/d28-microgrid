#!/usr/bin/env python3
"""REV16.1.3f — auditoria estatica, nao invasiva, G1/G2 e metadados HiGHS.
Nao importa o modelo, nao executa solver e nao autoriza NSGA-II.
"""
import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

G1 = Path('results/D28_REV16_1_3c_G1_CONSOLIDADO.json')
G2 = Path('results/D28_REV16_1_3e_G2_AUDITORIA.json')
OUT = Path('results/D28_REV16_1_3f_OTIMALIDADE.json')
SOURCE = [Path('src/d28/optimization/economic_dispatch_f1f2.py'),
          Path('src/d28/economics/f1.py'), Path('auditar_d28_rev16_1_3c.py'),
          Path('d28_rev16_1_3e_g2.py')]
SOLVER_KEYS = ('termination_condition','solver_status','best_bound','lower_bound',
               'upper_bound','mip_gap','relative_gap','absolute_gap','solver_time',
               'wallclock_time','objective_bound','optimality_gap','highs_status',
               'mip_node_count','node_count','solver_log','solver_metadata')

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding='utf-8-sig'))

def find_keys(obj, prefix='$', depth=0):
    if depth > 12:
        return []
    result=[]
    if isinstance(obj, dict):
        for k,v in obj.items():
            p=f'{prefix}.{k}'
            if any(t in k.lower() for t in SOLVER_KEYS):
                result.append({'path':p,'value':v if not isinstance(v,(dict,list)) else '<structured>'})
            result.extend(find_keys(v,p,depth+1))
    elif isinstance(obj,list):
        for i,v in enumerate(obj):
            result.extend(find_keys(v,f'{prefix}[{i}]',depth+1))
    return result

def finite_number(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--tolerance-brl',type=float,default=0.01,
                        help='Tolerancia absoluta para monotonicidade, R$/ano')
    parser.add_argument('--scan-logs',action='store_true',
                        help='Lista candidatos a logs (sem interpretar como certificado)')
    args=parser.parse_args()
    root=args.root.resolve()
    g1path=root/G1; g2path=root/G2
    report={'revision':'REV16.1.3f','scope':'STATIC_SOLVER_EVIDENCE_AND_MONOTONICITY',
            'generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'decision':'NSGA2_BLOCKED', 'milp_executed':False,
            'files':{},'findings':[],'rows':[],'monotonicity':[],'solver_metadata':{},
            'limitations':[]}
    def note(code,status,detail):
        report['findings'].append({'id':code,'status':status,'detail':detail})
    for rel in [G1,G2,*SOURCE]:
        p=root/rel
        report['files'][str(rel)]={'exists':p.is_file(),'sha256':digest(p) if p.is_file() else None}
    try:
        g1=read(g1path)
    except (OSError,ValueError) as exc:
        g1=None;note('G1_READ','BLOCKED',str(exc))
    try:
        g2=read(g2path)
    except (OSError,ValueError) as exc:
        g2=None;note('G2_READ','BLOCKED',str(exc))
    if not isinstance(g1,dict) or not isinstance(g1.get('rows'),list):
        note('G1_INPUT','BLOCKED','Relatorio G1 consolidado ausente ou invalido')
    else:
        note('G1_INPUT','PRESENT',f"revision={g1.get('revision')}; rows={len(g1['rows'])}")
        report['solver_metadata']['g1']=find_keys(g1)
        rows=[]
        for r in g1['rows']:
            if not isinstance(r,dict):continue
            e=r.get('epsilon_kw');c=r.get('milp_objective_brl');f2=r.get('f2_kw')
            bill=r.get('annual_energy_total_brl');pv=r.get('pv_total_cost_brl')
            if not all(finite_number(x) for x in (e,c,f2,bill,pv)):
                note('ROW_INVALID','BLOCKED',f'Linha sem valores numericos completos: {e}')
                continue
            entry={'epsilon_kw':e,'milp_objective_brl':c,'annual_energy_total_brl':bill,
                   'f2_kw':f2,'pv_total_cost_brl':pv,'status':r.get('status'),
                   'gate':r.get('gate'),'accounting_delta_brl':c-bill,
                   'solver_checks':r.get('solver_checks',{}),
                   'has_explicit_optimality_certificate':False}
            rows.append(entry)
        report['rows']=sorted(rows,key=lambda x:x['epsilon_kw'])
        if len(rows)!=4 or sorted(x['epsilon_kw'] for x in rows)!=[2300,2400,2450,2500]:
            note('FOUR_CASES','BLOCKED','Esperados exatamente 2300, 2400, 2450 e 2500 kW')
        else:note('FOUR_CASES','PASS','Quatro casos recuperados')
        for i,a in enumerate(report['rows']):
            for b in report['rows'][i+1:]:
                # Para epsilon maior, o custo otimo nao pode aumentar.
                delta=b['milp_objective_brl']-a['milp_objective_brl']
                # Teste da solucao anterior como referencia de factibilidade:
                feasible_at_b=a['f2_kw']<=b['epsilon_kw']+1e-6
                violation=feasible_at_b and delta>args.tolerance_brl
                report['monotonicity'].append({
                    'epsilon_restrictive_kw':a['epsilon_kw'],
                    'epsilon_relaxed_kw':b['epsilon_kw'],
                    'restrictive_solution_f2_kw':a['f2_kw'],
                    'restrictive_solution_feasible_for_relaxed_epsilon':feasible_at_b,
                    'cost_difference_relaxed_minus_restrictive_brl':delta,
                    'violation_beyond_tolerance':violation,
                    'interpretation':'POTENTIAL_NONOPTIMAL_INCUMBENT_OR_DIFFERENT_MODELS' if violation else 'NO_VIOLATION_DETECTED'})
        violations=[x for x in report['monotonicity'] if x['violation_beyond_tolerance']]
        note('MONOTONICITY','REVIEW' if violations else 'PASS',
             f'{len(violations)} violacoes acima de R$ {args.tolerance_brl:.2f}; '
             'comparacao presume mesmo modelo, dados e objetivo, exceto epsilon')
        if violations:
            note('OPTIMALITY_CERTIFICATION','NOT_CERTIFIED',
                 'PASS de factibilidade/contabilidade nao e certificado de otimalidade global')
    if isinstance(g2,dict):
        report['solver_metadata']['g2']=find_keys(g2)
        note('G2_INPUT','PRESENT','Relatorio G2 localizado; nao sera modificado')
    else:note('G2_INPUT','MISSING','Relatorio G2 ausente ou invalido')
    metadata=report['solver_metadata'].get('g1',[])
    certified_fields=[x for x in metadata if any(s in x['path'].lower() for s in
                     ('best_bound','lower_bound','mip_gap','termination_condition','optimality_gap'))]
    note('SOLVER_CERTIFICATE','FOUND_REVIEW_REQUIRED' if certified_fields else 'MISSING',
         'Metadados candidatos encontrados; verificar origem e valores' if certified_fields else
         'G1 nao registra limite inferior, MIP gap e termino suficientes para certificar otimalidade')
    if args.scan_logs:
        logs=[]
        for base in (root/'results',root/'logs'):
            if base.is_dir():
                for p in base.rglob('*'):
                    if p.is_file() and p.suffix.lower() in ('.log','.txt','.sol','.json'):
                        if re.search(r'(highs|solver|milp|rev16_1_3)',p.name,re.I):
                            logs.append({'path':str(p.relative_to(root)),
                                         'size_bytes':p.stat().st_size})
        report['candidate_log_files']=logs[:200]
    report['limitations']=[
        'Nao reconstroi o modelo nem comprova identidade de dados entre execucoes.',
        'F2 e custo dos JSON nao constituem solucao primal completa reutilizavel como warm start.',
        'Sem lower bound, MIP gap e termination condition nao se certifica otimalidade.',
        'Monotonicidade compara incumbentes registrados, nao valores otimos certificados.',
        'Nao altera G1/G2, configuracoes, scripts ou resultados existentes.',
        'NSGA-II permanece bloqueado independentemente dos resultados desta auditoria.'
    ]
    out=root/OUT;out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REV16.1.3f | AUDITORIA ESTATICA')
    for f in report['findings']:
        print(f"{f['id']}: {f['status']} — {f['detail']}")
    for x in report['monotonicity']:
        if x['violation_beyond_tolerance']:
            print(f"VIOLACAO: {x['epsilon_restrictive_kw']:.0f}->{x['epsilon_relaxed_kw']:.0f} kW | "
                  f"custo +R$ {x['cost_difference_relaxed_minus_restrictive_brl']:.4f}")
    print('NSGA2_AUTHORIZED: False')
    print('REPORT:',out)

if __name__=='__main__':main()
