from d28.optimization.architecture_evaluator import evaluate_design_rev081

def test_unknown_architecture():
    r=evaluate_design_rev081("R9",{"pv_kw":0,"bess_kwh":0,"pcs_kw":0},[10],[0])
    assert not r.feasible and r.objectives is None

def test_invalid_pcs():
    r=evaluate_design_rev081("R0",{"pv_kw":0,"bess_kwh":100,"pcs_kw":100},[10],[0])
    assert not r.feasible and r.objectives is None

def test_missing_chp():
    r=evaluate_design_rev081("R1",{"pv_kw":0,"bess_kwh":100,"pcs_kw":10},[10],[0])
    assert not r.feasible and "CHP" in r.reason

def test_r0_physical_gate():
    r=evaluate_design_rev081("R0",{"pv_kw":0,"bess_kwh":100,"pcs_kw":10},[10,10,10,10],[0,0,0,0],pcc_cap_kw=100)
    assert not r.feasible and r.objectives is None
    assert r.audit["F2_kw"] is not None
    assert r.audit["max_balance_residual_kw"]<1e-5
    assert not r.audit["scientific_pareto_eligible"]
