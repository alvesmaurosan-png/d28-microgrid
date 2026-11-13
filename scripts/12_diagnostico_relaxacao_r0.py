"""D28: diagnostico ADITIVO de factibilidade R0, sem alterar modelo original.
LP e MILP usam as mesmas equacoes; LP relaxa apenas a integralidade de bess_mode.
Folgas diagnosticas nunca podem ser utilizadas no calculo de F1/F2.
"""
import argparse, json, sys, math
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import pyomo.environ as p
from pyomo.contrib.appsi.solvers import Highs
from d28.optimization.synthetic_reference_rev11 import load_reference, read_json
from d28.optimization.biobjective_milp_connector import build_route_milp


def build_diagnostic(inputs,design,*,integer=False,policy='physical'):
    m=build_route_milp('R0',design,inputs)
    ts=list(m.T); n=len(ts); cap=float(inputs.pcc_cap_kw)
    # Preservar as equacoes: relaxar apenas limites especificados, em uma COPIA diagnostica.
    for o in m.component_data_objects(p.Objective,active=True):o.deactivate()
    if not integer:
        for t in ts:m.bess_mode[t].domain=p.UnitInterval
    # Pesos por kWh de violacao; para SOC terminal/estoque converter kWh diretamente.
    weights=({'deficit':1e6,'surplus':1e6,'pcc':1.,'soc':1e4,'pcs':1e4,'terminal':1e3}
             if policy=='physical' else
             {'deficit':1e6,'surplus':1e6,'pcc':1e5,'soc':1e3,'pcs':1e3,'terminal':1e2})
    m.diag=p.Block(); d=m.diag
    d.deficit=p.Var(m.T,domain=p.NonNegativeReals)
    d.surplus=p.Var(m.T,domain=p.NonNegativeReals)
    d.pcc=p.Var(m.T,domain=p.NonNegativeReals)
    d.soc_low=p.Var(m.S,domain=p.NonNegativeReals)
    d.soc_high=p.Var(m.S,domain=p.NonNegativeReals)
    d.pcs_charge=p.Var(m.T,domain=p.NonNegativeReals)
    d.pcs_discharge=p.Var(m.T,domain=p.NonNegativeReals)
    d.term_pos=p.Var(domain=p.NonNegativeReals)
    d.term_neg=p.Var(domain=p.NonNegativeReals)
    for t in ts:
        m.grid[t].setub(None)
        m.balance[t].deactivate()
        m.bess_charge_limit[t].deactivate()
        m.bess_discharge_limit[t].deactivate()
    for s in m.S:
        m.bess_energy[s].domain=p.Reals
        m.bess_energy[s].setlb(None)
        m.bess_energy[s].setub(None)
    d.balance=p.Constraint(m.T,rule=lambda b,t:
        m.grid[t]+m.pv[t]+m.bess_discharge[t]+d.deficit[t]
        ==m.load_kw[t]+m.bess_charge[t]+d.surplus[t])
    d.pcc_cap=p.Constraint(m.T,rule=lambda b,t:m.grid[t]<=cap+d.pcc[t])
    lo=.1*design['bess_kwh'];hi=.9*design['bess_kwh']
    d.soc_min=p.Constraint(m.S,rule=lambda b,t:m.bess_energy[t]>=lo-d.soc_low[t])
    d.soc_max=p.Constraint(m.S,rule=lambda b,t:m.bess_energy[t]<=hi+d.soc_high[t])
    d.pcs_c=p.Constraint(m.T,rule=lambda b,t:m.bess_charge[t]<=design['pcs_kw']*m.bess_mode[t]+d.pcs_charge[t])
    d.pcs_d=p.Constraint(m.T,rule=lambda b,t:m.bess_discharge[t]<=design['pcs_kw']*(1-m.bess_mode[t])+d.pcs_discharge[t])
    if hasattr(m,'bess_terminal'):
        m.bess_terminal.deactivate()
        d.terminal=p.Constraint(expr=m.bess_energy[n]-m.bess_energy[0]==d.term_pos-d.term_neg)
    else:
        d.term_pos.fix(0);d.term_neg.fix(0)
    dt=float(inputs.dt_hours)
    d.objective=p.Objective(expr=
        dt*sum(weights['deficit']*d.deficit[t]+weights['surplus']*d.surplus[t]
            +weights['pcc']*d.pcc[t]+weights['pcs']*(d.pcs_charge[t]+d.pcs_discharge[t]) for t in ts)
        +weights['soc']*sum(d.soc_low[t]+d.soc_high[t] for t in m.S)
        +weights['terminal']*(d.term_pos+d.term_neg),sense=p.minimize)
    return m,weights


def solve_and_report(m,inputs,design,weights,*,integer,policy,time_limit):
    s=Highs();s.config.load_solution=False;s.config.time_limit=time_limit
    r=s.solve(m)
    out={'status':str(r.termination_condition),'mode':'MILP' if integer else 'LP_RELAXATION',
         'policy':policy,'solver_best_feasible_objective':r.best_feasible_objective,
         'solver_best_objective_bound':r.best_objective_bound,
         'intervals':len(inputs.load_kw),'dt_hours':inputs.dt_hours,'weights':weights,
         'design':design,'not_valid_for_f1_f2':True}
    if r.best_feasible_objective is None:
        out['diagnosis']='NO_FEASIBLE_RELAXED_SOLUTION_OR_TIME_LIMIT'
        return out
    s.load_vars();d=m.diag;dt=float(inputs.dt_hours)
    groups={'deficit':(d.deficit,dt),'surplus':(d.surplus,dt),'pcc':(d.pcc,dt),
            'soc_low':(d.soc_low,1.),'soc_high':(d.soc_high,1.),
            'pcs_charge':(d.pcs_charge,dt),'pcs_discharge':(d.pcs_discharge,dt)}
    summary={};top={}
    for name,(var,factor) in groups.items():
        arr=[(int(t),float(p.value(var[t]))) for t in var]
        nonzero=[(t,v) for t,v in arr if v>1e-5]
        summary[name]={'violated_intervals':len(nonzero),'sum_raw':sum(v for _,v in nonzero),
                       'sum_kwh_equivalent':sum(v for _,v in nonzero)*factor,
                       'max_value':max((v for _,v in nonzero),default=0.)}
        top[name]=[{'interval_index':t,'value':v} for t,v in sorted(nonzero,key=lambda a:-a[1])[:15]]
    out['violations']=summary;out['top_violations']=top
    out['terminal_deviation_kwh']=float(p.value(d.term_pos)-p.value(d.term_neg))
    out['weighted_objective']=float(p.value(d.objective))
    out['all_slacks_zero']=all(v['max_value']<=1e-5 for v in summary.values()) and abs(out['terminal_deviation_kwh'])<=1e-5
    out['interpretation']=('NO_VIOLATION_IN_DIAGNOSTIC_MODEL' if out['all_slacks_zero'] else
                            'RELAXED_FEASIBLE_ONLY; ORIGINAL_CONSTRAINTS_VIOLATED')
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scenario',default='E100',choices=['E100','E200','E300','E375','E450'])
    ap.add_argument('--pv',type=float,default=1908.225)
    ap.add_argument('--bess',type=float,default=10000.)
    ap.add_argument('--pcs',type=float,default=5500.)
    ap.add_argument('--mode',choices=['lp','milp'],default='lp')
    ap.add_argument('--policy',choices=['physical','protect-pcc'],default='physical')
    ap.add_argument('--time-limit',type=float,default=600)
    ap.add_argument('--intervals',type=int,default=0,help='0=ano completo; valor positivo para piloto, nao conclusivo')
    args=ap.parse_args()
    settings=read_json(ROOT/'config/synthetic_reference_rev11.json')
    _,inputs,_,_,_,_,provenance=load_reference(ROOT,args.scenario,'R0',settings)
    if args.intervals:
        from dataclasses import replace
        if args.intervals<1 or args.intervals>len(inputs.load_kw):raise ValueError('INVALID_INTERVALS')
        inputs=replace(inputs,load_kw=inputs.load_kw[:args.intervals],pv_pu=inputs.pv_pu[:args.intervals],months=inputs.months[:args.intervals])
    design={'pv_kw':args.pv,'bess_kwh':args.bess,'pcs_kw':args.pcs}
    model,weights=build_diagnostic(inputs,design,integer=args.mode=='milp',policy=args.policy)
    report=solve_and_report(model,inputs,design,weights,integer=args.mode=='milp',policy=args.policy,time_limit=args.time_limit)
    report['provenance']=provenance
    report['annual_scope']=len(inputs.load_kw)==35040
    report['scientific_status']='DIAGNOSTIC_ONLY_NOT_AN_OPTIMIZATION_RESULT'
    target=ROOT/'results'/f'rev12_relax_{args.scenario}_{args.mode}_{args.policy}.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print('TERMINATION:',report['status']);print('REPORT:',target)
    for k,v in report.get('violations',{}).items():print(k,'count=',v['violated_intervals'],'max=',round(v['max_value'],4),'kWh-equivalent=',round(v['sum_kwh_equivalent'],4))
    print('TERMINAL_KWH:',report.get('terminal_deviation_kwh'))
    return 0 if 'violations' in report else 2

if __name__=='__main__':raise SystemExit(main())
