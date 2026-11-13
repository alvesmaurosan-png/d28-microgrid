"""Preflight default; --solve invokes actual 35040 interval Pyomo MILP; --nsga2 expensive."""
import sys, argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from d28.optimization.synthetic_reference_rev11 import evaluate,make_problem,read_json

def main():
 p=argparse.ArgumentParser();p.add_argument('--scenario',choices=['E100','E200','E300','E375','E450'],default='E100')
 p.add_argument('--route',choices=['R0','R1','R2','R3'],default='R0')
 p.add_argument('--pv',type=float,default=1908.225);p.add_argument('--bess',type=float,default=10000.)
 p.add_argument('--pcs',type=float,default=5500.);p.add_argument('--solve',action='store_true')
 p.add_argument('--nsga2',action='store_true');p.add_argument('--pop',type=int,default=8);p.add_argument('--gens',type=int,default=2)
 p.add_argument('--solver',default='appsi_highs');args=p.parse_args()
 settings=read_json(ROOT/'config/synthetic_reference_rev11.json');design={'pv_kw':args.pv,'bess_kwh':args.bess,'pcs_kw':args.pcs}
 out=ROOT/'results';out.mkdir(exist_ok=True)
 target=out/f'rev11_{args.route}_{args.scenario}.json'
 try:
  if args.nsga2:
   if not args.solve:raise ValueError('NSGA2_REQUIRES_EXPLICIT_SOLVE')
   if args.pop<4 or args.gens<1:raise ValueError('INVALID_NSGA2_BUDGET')
   from pymoo.algorithms.moo.nsga2 import NSGA2
   from pymoo.optimize import minimize
   bounds={'pv_kw':(0,1908.225),'bess_kwh':(0,30000.),'pcs_kw':(0,16500.)}
   problem=make_problem(ROOT,args.scenario,args.route,settings,bounds,args.solver)
   opt=minimize(problem,NSGA2(pop_size=args.pop),('n_gen',args.gens),seed=42,verbose=False)
   payload={'mode':'NSGA2_SYNTHETIC','route':args.route,'scenario':args.scenario,
    'evaluations':problem.records,'F':None if opt.F is None else opt.F.tolist(),
    'X':None if opt.X is None else opt.X.tolist(),'f3_excluded':True}
  else:payload=evaluate(ROOT,args.scenario,args.route,design,settings,run_solver=args.solve,solver_name=args.solver)
 except Exception as exc:payload={'status':'BLOCKED_OR_FAILED','error':f'{type(exc).__name__}: {exc}','milp_executed':False}
 target.write_text(json.dumps(payload,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
 print('STATUS:',payload.get('status',payload.get('mode')));print('REPORT:',target)
 if payload.get('objectives'):print('F1,F2:',payload['objectives'])
 if payload.get('error'):print('ERROR:',payload['error'])
 return 0 if payload.get('status') in ('PREFLIGHT_ONLY','OPTIMAL_SYNTHETIC','PROVEN_INFEASIBLE_NECESSARY_CONDITION') or payload.get('mode')=='NSGA2_SYNTHETIC' else 2
if __name__=='__main__':raise SystemExit(main())
