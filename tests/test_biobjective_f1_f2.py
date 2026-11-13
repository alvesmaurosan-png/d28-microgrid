from d28.optimization.biobjective_f1_f2 import evaluate_biobjective

def test_valid_pair():
    r = evaluate_biobjective('R0', {}, build_model=lambda r,d: object(),
        solve_dispatch=lambda m: {'optimal':True,'grid_kw':[12,5,7]},
        compute_f1=lambda m,s,d:0.42, annual_verified=True)
    assert r.feasible and r.objectives == (0.42,12.0)

def test_no_annual_extrapolation():
    r = evaluate_biobjective('R2', {}, build_model=lambda r,d: object(),
        solve_dispatch=lambda m: {'optimal':True,'grid_kw':[12,5]},
        compute_f1=lambda m,s,d:0.42, annual_verified=False)
    assert not r.feasible and r.status == 'ANNUAL_EVIDENCE_REQUIRED'

def test_f3_not_required():
    r = evaluate_biobjective('R3', {}, build_model=lambda r,d: object(),
        solve_dispatch=lambda m: {'optimal':True,'grid_kw':[1]},
        compute_f1=lambda m,s,d:0.3, annual_verified=True)
    assert r.objectives == (0.3,1.0)

def test_infeasible_not_pareto():
    r = evaluate_biobjective('R1', {}, build_model=lambda r,d: object(),
        solve_dispatch=lambda m: {'optimal':False,'grid_kw':[]},
        compute_f1=lambda m,s,d:0.3, annual_verified=True)
    assert not r.feasible and r.objectives is None
