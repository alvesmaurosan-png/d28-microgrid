"""NSGA-II + MILP R0. Modo smoke nao produz fronteira cientifica."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import pyomo.environ as pe
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from d28.dispatch.milp import build_r0_milp
from d28.optimization.r0_pipeline import validate_assumptions, evaluate_objectives


def load_day(path, day):
    with open(path,encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=35040:
        raise ValueError('Esperados 35040 intervalos, recebidos '+str(len(rows)))
    selected=rows[day*96:(day+1)*96]
    load=np.array([float(r['load_charging_ac_kw']) for r in selected])
    pv=np.array([float(r['pv_kw_per_kwp']) for r in selected])
    if not (np.all(np.isfinite(load)) and np.all(np.isfinite(pv)) and np.all(load>=0) and np.all(pv>=0)):
        raise ValueError('Series com valores invalidos')
    return load,pv


def solve_lex(load,solar,pv_kw,bess_kwh,pcs_kw,pcc_kw=2500.):
    if pcs_kw>0.55*bess_kwh+1e-9:
        return None
    m=build_r0_milp(load_kw=load.tolist(),pv_pu=solar.tolist(),pv_capacity_kw=float(pv_kw),
                    bess_capacity_kwh=float(bess_kwh),pcs_power_kw=float(pcs_kw),
                    pcc_cap_kw=pcc_kw,dt_hours=.25,terminal_policy='cyclic')
    for obj in m.component_objects(pe.Objective,active=True):
        obj.deactivate()
    m.peak_import=pe.Var(domain=pe.NonNegativeReals,bounds=(0,pcc_kw))
    m.peak_limits=pe.Constraint(m.T,rule=lambda model,t:model.grid[t]<=model.peak_import)
    m.primary=pe.Objective(expr=m.peak_import,sense=pe.minimize)
    solver=pe.SolverFactory('appsi_highs')
    if not solver.available():
        raise RuntimeError('HiGHS indisponivel')
    solver.config.load_solution=False
    try:
        solver.config.load_solution = False
        first = solver.solve(m, load_solutions=False)

        if first.solver.termination_condition!=pe.TerminationCondition.optimal:
            return None
        m.solutions.load_from(first)
        optimum=float(pe.value(m.peak_import))
        m.primary.deactivate()
        m.peak_tolerance=pe.Constraint(expr=m.peak_import<=optimum+1e-5)
        m.secondary=pe.Objective(expr=.25*sum(m.grid[t] for t in m.T),sense=pe.minimize)
        second=solver.solve(m, load_solutions=False)
        if second.solver.termination_condition!=pe.TerminationCondition.optimal:
            return None
        m.solutions.load_from(second)
    except (ValueError,RuntimeError) as exc:
        if 'infeasib' in str(exc).lower() or 'no feasible' in str(exc).lower():
            return None
        raise
    grid=np.array([pe.value(m.grid[t]) for t in m.T],dtype=float)
    pv_used=np.array([pe.value(m.pv[t]) for t in m.T],dtype=float)
    charge=np.array([pe.value(m.bess_charge[t]) for t in m.T],dtype=float)
    discharge=np.array([pe.value(m.bess_discharge[t]) for t in m.T],dtype=float)
    residual=float(np.max(np.abs(grid+pv_used+discharge-load-charge)))
    if residual>1e-5 or np.max(grid)>pcc_kw+1e-5:
        raise RuntimeError(f'Falha fisica: residual={residual}')
    return {'F2_kw':float(np.max(grid)),'grid_energy_kwh':float(.25*np.sum(grid)),
            'pv_used_kwh':float(.25*np.sum(pv_used)),'balance_residual_kw':residual,
            'pcc_utilization':float(np.max(grid)/pcc_kw)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode',choices=['smoke','scientific'],default='smoke')
    ap.add_argument('--day',type=int,default=216)
    ap.add_argument('--population',type=int,default=8)
    ap.add_argument('--generations',type=int,default=2)
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--regression',action='store_true')
    args=ap.parse_args()
    if not 0<=args.day<365: raise ValueError('day deve estar entre 0 e 364')
    if args.population<4 or args.generations<1: raise ValueError('Orcamento invalido')
    root=Path(__file__).resolve().parents[3]
    data=root/'data/processed/milp_inputs/R0_inputs_E100_15min.csv'
    load,solar=load_day(data,args.day)
    config_path=root/'config/experiments/r0_objective_inputs.json'
    assumptions=None
    if args.mode=='scientific':
        assumptions=json.loads(config_path.read_text(encoding='utf-8'))
        validate_assumptions(assumptions)
        if args.day!=0:
            raise RuntimeError('F1/F3 anuais nao podem ser calculadas a partir de 24h; execucao cientifica anual ainda nao implementada')
        raise RuntimeError('Execucao cientifica bloqueada: falta avaliacao anual e fronteira economica/ACV integral')
    if args.regression:
        baseline=solve_lex(load,solar,5000.,20000.,5000.)
        if baseline is None:
            raise RuntimeError('Regressao: configuracao anterior tornou-se inviavel')
        # O resultado anterior minimizou apenas o pico; a segunda etapa nao pode elevar F2 alem da tolerancia.
        if baseline['F2_kw']>360.32093425370306+1e-3:
            raise RuntimeError('Regressao: pico superior ao resultado anterior')
        print('REGRESSION_OK',json.dumps(baseline,ensure_ascii=False))
    # Faixas exploratorias exclusivamente para teste de integracao, nao limites homologados de projeto.
    lower=np.array([0.,1000.,0.])
    upper=np.array([5000.,20000.,5000.])
    class Problem(ElementwiseProblem):
        def __init__(self):
            super().__init__(n_var=3,n_obj=2,n_ieq_constr=1,xl=lower,xu=upper)
            self.calls=0
            self.feasible=0
        def _evaluate(self,x,out,*args,**kwargs):
            self.calls+=1
            pv,bess,pcs=map(float,x)
            violation=max(0.,pcs-.55*bess)
            if violation>0:
                out['G']=[violation]
                out['F']=[1e12,1e12]
                return
            r=solve_lex(load,solar,pv,bess,pcs)
            if r is None:
                out['G']=[1.]
                out['F']=[1e12,1e12]
                return
            self.feasible+=1
            # Indicador de tamanho adimensional para smoke; NAO e F1.
            size=pv/5000.+bess/20000.+pcs/5000.
            out['G']=[-1.]
            out['F']=[size,r['F2_kw']]
    problem=Problem()
    res=minimize(problem,NSGA2(pop_size=args.population),termination=('n_gen',args.generations),
                 seed=args.seed,verbose=False)
    output=root/'results/r0_nsga2_smoke'
    output.mkdir(parents=True,exist_ok=True)
    solutions=[]
    if res.X is not None:
        xs=np.atleast_2d(res.X)
        fs=np.atleast_2d(res.F)
        for x,f in zip(xs,fs):
            solutions.append({'pv_kwp':float(x[0]),'bess_kwh':float(x[1]),'pcs_kw':float(x[2]),
                              'size_index_NOT_F1':float(f[0]),'F2_24h_kw':float(f[1])})
    with (output/'pareto_smoke.csv').open('w',encoding='utf-8',newline='') as f:
        cols=['pv_kwp','bess_kwh','pcs_kw','size_index_NOT_F1','F2_24h_kw']
        writer=csv.DictWriter(f,fieldnames=cols)
        writer.writeheader()
        writer.writerows(solutions)
    summary={'status':'SMOKE_ONLY_NOT_SCIENTIFIC','scenario':'E100','day_index':args.day,
             'population':args.population,'generations':args.generations,'seed':args.seed,
             'evaluations':problem.calls,'feasible_evaluations':problem.feasible,
             'pareto_solutions':len(solutions),'F1':'NOT_COMPUTED','F3':'NOT_COMPUTED',
             'result_csv':str((output/'pareto_smoke.csv').relative_to(root))}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
