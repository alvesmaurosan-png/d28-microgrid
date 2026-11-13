"""M2: comparison of identical synthetic R0 LP using Pyomo/HiGHS and SciPy/HiGHS.
This is a numerical/software smoke test, NOT D28 scientific validation.
"""
from __future__ import annotations
import argparse, json, platform, sys, hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from d28.dispatch.milp import build_r0_smoke

LOAD = np.array([100., 150., 120., 80.])
PV_PU = np.array([0., .3, .5, .1])
PV_CAP = 100.
PCC_CAP = 2500.
DT_H = .25
TOL = 1e-6  # software smoke numerical tolerance; NOT scientific optimization tolerance

def scipy_solve():
    n = len(LOAD)
    A = lil_matrix((n, 2*n))
    for i in range(n):
        A[i,i] = 1.; A[i,n+i] = 1.
    result = milp(np.r_[np.ones(n),np.zeros(n)],
                  bounds=Bounds(np.zeros(2*n),np.r_[np.full(n,PCC_CAP),PV_CAP*PV_PU]),
                  constraints=LinearConstraint(A.tocsr(),LOAD,LOAD))
    if not result.success: raise RuntimeError(f'SciPy/HiGHS: {result.message}')
    return {'grid_kw':result.x[:n].tolist(),'pv_kw':result.x[n:].tolist(), 'objective_sum_grid_kw':float(result.fun)}

def pyomo_solve():
    import pyomo.environ as p
    import pyomo, highspy
    m = build_r0_smoke(LOAD.tolist(), PV_PU.tolist(), PV_CAP, PCC_CAP)
    solver = p.SolverFactory('appsi_highs')
    if not solver.available(exception_flag=False): raise RuntimeError('appsi_highs indisponível')
    result = solver.solve(m)
    termination = str(result.solver.termination_condition)
    if termination.lower() != 'optimal': raise RuntimeError(f'Pyomo: {termination}')
    return {'grid_kw':[float(p.value(m.grid[t])) for t in m.T],
            'pv_kw':[float(p.value(m.pv[t])) for t in m.T],
            'objective_sum_grid_kw':float(p.value(m.obj)),
            'termination':termination,
            'versions':{'pyomo':getattr(pyomo,'__version__','unknown'),
                        'highspy':getattr(highspy,'__version__','unknown')}}

def validate(sol):
    g = np.asarray(sol['grid_kw']); pv=np.asarray(sol['pv_kw'])
    return {'max_balance_residual_kw':float(np.max(np.abs(g+pv-LOAD))),
            'max_pv_violation_kw':float(np.max(np.maximum(pv-PV_CAP*PV_PU,0))),
            'max_pcc_violation_kw':float(np.max(np.maximum(g-PCC_CAP,0))),
            'min_grid_kw':float(np.min(g)), 'min_pv_kw':float(np.min(pv)),
            'grid_energy_kwh':float(np.sum(g)*DT_H)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(ROOT/'experiments/manifests/M2_pyomo_vs_scipy.json'))
    args=parser.parse_args()
    evidence={'gate':'M2','scope':'synthetic_R0_four_15min_intervals','scientific_validation':False,
              'python':platform.python_version(), 'input':{'load_kw':LOAD.tolist(),'pv_pu':PV_PU.tolist(),
              'pv_capacity_kw':PV_CAP,'pcc_cap_kw':PCC_CAP,'delta_t_h':DT_H},
              'tolerance_numerical_smoke':TOL}
    evidence['scipy']=scipy_solve()
    evidence['scipy']['checks']=validate(evidence['scipy'])
    try:
        evidence['pyomo']=pyomo_solve()
        evidence['pyomo']['checks']=validate(evidence['pyomo'])
        a,b=evidence['scipy'],evidence['pyomo']
        evidence['comparison']={'max_abs_grid_diff_kw':float(np.max(np.abs(np.array(a['grid_kw'])-b['grid_kw']))),
              'max_abs_pv_diff_kw':float(np.max(np.abs(np.array(a['pv_kw'])-b['pv_kw']))),
              'abs_objective_diff':abs(a['objective_sum_grid_kw']-b['objective_sum_grid_kw'])}
        evidence['passed']=all(v<=TOL for v in evidence['comparison'].values()) and all(
            evidence[solver]['checks'][key]<=TOL for solver in ('scipy','pyomo') for key in
            ('max_balance_residual_kw','max_pv_violation_kw','max_pcc_violation_kw'))
        evidence['status']='PASS' if evidence['passed'] else 'FAIL'
    except (ImportError,RuntimeError) as exc:
        evidence['status']='BLOCKED_PYOMO_ENVIRONMENT'
        evidence['reason']=str(exc)
        evidence['passed']=False
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))
    return 0 if evidence['passed'] else 2

if __name__=='__main__':raise SystemExit(main())
