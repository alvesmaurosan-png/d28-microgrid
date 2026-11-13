"""Executa uma avaliação científica anual F1/F2, com evidências externas homologadas."""
import argparse, importlib, json, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--route',required=True,choices=['R0','R1','R2','R3'])
    ap.add_argument('--contract',required=True,type=Path)
    ap.add_argument('--design',required=True,type=Path)
    ap.add_argument('--factory',required=True,help='modulo:funcao, factory(route,design)->AnnualEvidence')
    ap.add_argument('--epsilon-kw',type=float,default=None,help='Reservado; nao suportado neste conector')
    a=ap.parse_args()
    if a.epsilon_kw is not None: ap.error('epsilon ainda nao e propagado pelo conector anual')
    from d28.optimization.r0_r3_bridge import annual_contract_ready
    contract=json.loads(a.contract.read_text(encoding='utf-8-sig'))
    ready,reason=annual_contract_ready(contract)
    if not ready: raise SystemExit('BLOQUEADO: '+reason)
    design=json.loads(a.design.read_text(encoding='utf-8-sig'))
    module,sep,attr=a.factory.partition(':')
    if not sep: ap.error('--factory deve ser modulo:funcao')
    factory=getattr(importlib.import_module(module),attr)
    from d28.optimization.annual_f1_f2_connector_rev06 import evaluate_annual
    result=evaluate_annual(a.route,design,contract=contract,evidence_factory=factory)
    report={'route':a.route,'feasible':result.feasible,'status':result.status,'objectives':result.objectives,'audit':result.audit}
    Path('results').mkdir(exist_ok=True)
    output=Path('results')/f'F1_F2_ANUAL_{a.route}_REV16_1.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({'status':result.status,'feasible':result.feasible,'objectives':result.objectives,'report':str(output)},ensure_ascii=False))
    if not result.feasible: sys.exit(2)
if __name__=='__main__':main()
