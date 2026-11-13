"""Teste único de integração REV16.1: gate real + circuito NSGA-II de interface.
Não aprova evidências, não reexecuta MILP anual, não inventa F1.
"""
import json, sys, hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

def load(p):
    with open(ROOT/p,encoding='utf-8') as f:return json.load(f)

def main():
    from d28.optimization.r0_r3_bridge import annual_contract_ready
    from d28.optimization.d28_adapter_f1f2_nsga2 import evaluate_design, as_pymoo_problem
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.optimize import minimize
    report={'test':'D28_REV16_1_SINGLE_INTEGRATION','timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'scientific_pareto_certified':False,'milp_reexecuted':False,'f3_excluded':True}
    contract=load('config/contrato_sintetico_rev11.json')
    evidence=load('config/annual_f1_f2_evidence.json')
    ready,reason=annual_contract_ready(contract)
    report['contract']={'ready':ready,'reason':reason,'scope':contract.get('scope'),
                        'interpretation':contract.get('interpretation')}
    report['evidence']={'status':evidence.get('status'),'approved':evidence.get('status')=='APPROVED'}
    # Teste de integração real da interface, sem simular homologação ou solver.
    called=[]
    def forbidden(*args,**kwargs):
        called.append(True)
        raise AssertionError('MILP não deve ser executado com evidência não homologada')
    def evaluator(design):
        return evaluate_design('R0',design,contract=contract,
              evidence_approved=report['evidence']['approved'],
              provenance={'source':'config/annual_f1_f2_evidence.json'},
              solve_annual_economic=forbidden,reconcile_annual=forbidden)
    problem=as_pymoo_problem('R0',{'pv_kwp':(100.,300.),'bess_kwh':(10000.,30000.)},evaluator)
    result=minimize(problem,NSGA2(pop_size=4),termination=('n_gen',2),seed=42,verbose=False)
    records=problem.records
    statuses=sorted(set(r['status'] for r in records))
    report['nsga2_interface']={'executed':True,'evaluations':len(records),'statuses':statuses,
        'feasible_count':sum(bool(r['feasible']) for r in records),
        'solver_callback_calls':len(called),'objective_count':2,
        'note':'Teste de integração da interface e do bloqueio; NÃO é execução científica MILP+F1/F2.'}
    blockers=[]
    if not ready:blockers.append('ANNUAL_CONTRACT_BLOCKED: '+reason)
    if not report['evidence']['approved']:blockers.append('ANNUAL_F1_F2_EVIDENCE_NOT_HOMOLOGATED')
    blockers.append('ECONOMIC_DISPATCH_F1_F2_NOT_CERTIFIED_FOR_PARETO')
    report['blockers']=blockers
    report['conclusion']='INTEGRATION_INTERFACE_PASS_SCIENTIFIC_EXECUTION_BLOCKED'
    assert len(records)>0 and len(called)==0 and all(not r['feasible'] for r in records)
    out=ROOT/'reports'/'D28_TESTE_UNICO_INTEGRACAO_REV16_1.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    print('RELATORIO:',out)

if __name__=='__main__':main()
