from d28.optimization.integrated_evaluator import (
    DesignR0, Evaluation, evaluate_population, to_pymoo_result, evaluate_r0)
import pytest

def test_loop_feedback():
    pop = [DesignR0(0,0,0), DesignR0(100,200,110)]
    out = evaluate_population(pop, lambda d: Evaluation(True,(d.pv_kwp,10,1),"",{}))
    assert to_pymoo_result(out) == [[0,10,1],[100,10,1]]

def test_missing_acv_blocks_f3():
    e = evaluate_r0(DesignR0(0,0,0),load_kw=[100],pv_pu=[0],
                    months=[202601],economics=None,annual_pkm=100,
                    lifecycle_kgco2e=None)
    assert not e.feasible and e.objectives is None

def test_infeasible_never_fabricates_objectives():
    with pytest.raises(ValueError):
        to_pymoo_result([Evaluation(False,None,"MILP inviável",{})])
