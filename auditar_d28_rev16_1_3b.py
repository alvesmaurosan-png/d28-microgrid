#!/usr/bin/env python3
"""REV16.1.3b: reconcilia faturamento e VP; MILP requer objetivo explícito."""
import json, math, argparse
from pathlib import Path

def num(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--report',default='results/D28_REV16_1_3a_G1.json')
    p.add_argument('--output',default='results/D28_REV16_1_3b_RECONCILIACAO.json')
    a=p.parse_args()
    source=Path(a.report)
    if not source.is_file(): p.error(f'Arquivo ausente: {source}')
    data=json.loads(source.read_text(encoding='utf-8-sig'))
    results=[]
    for r in data.get('rows',[]):
        energy=r.get('annual_energy_charge_brl'); demand=r.get('annual_demand_charge_brl')
        billed=r.get('annual_energy_total_brl'); pv=r.get('pv_total_cost_brl')
        ok=all(map(num,(energy,demand,billed,pv)))
        delta=billed-energy-demand if ok else None
        bill_ok=ok and math.isclose(delta,0,abs_tol=1e-4,rel_tol=1e-9)
        results.append({'epsilon_kw':r.get('epsilon_kw'),'solver_status':r.get('status'),
          'C_MILP_brl':'NOT_EXPOSED_IN_G1_REPORT',
          'C_faturamento_anual_brl':billed,'C_energia_anual_brl':energy,
          'C_demanda_anual_brl':demand,'residuo_faturamento_brl':delta,
          'C_VP_total_brl':pv,'faturamento_identidade': 'PASS' if bill_ok else 'REVIEW',
          'milp_vs_faturamento':'PENDING_OBJECTIVE_DECOMPOSITION',
          'vp_vs_faturamento':'PENDING_CAPEX_OPEX_DISCOUNT_DECOMPOSITION',
          'status':'PARTIAL' if bill_ok and r.get('status')=='PASS' else 'REVIEW'})
    report={'revision':'REV16.1.3b','source':str(source),'classification':'DIAGNOSTIC_NOT_HOMOLOGATED',
       'conclusion':'PARTIAL_ONLY_NO_MILP_OBJECTIVE_OR_VP_DECOMPOSITION', 'rows':results,
       'required_evidence':['objective_value and objective terms from solve_economic',
       'annual_variable_bill and cost breakdown from present_value',
       'tariff demand charge inclusion/exclusion in MILP objective']}
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    for r in results: print(f"epsilon={r['epsilon_kw']} | faturamento={r['faturamento_identidade']} | MILP=PENDENTE | VP=PENDENTE")
    print('RELATORIO:',dest)
    return 0 if results and all(r['status']=='PARTIAL' for r in results) else 2
if __name__=='__main__': raise SystemExit(main())
