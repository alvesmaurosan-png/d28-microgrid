import pytest
from d28.rev02.chp_nsga2 import optimize_chp_synthetic
from d28.rev02.chp_integration import CHPCase
from d28.rev02.chp import CHPParameters
from d28.rev02.operational_integration import OperationalCase
from d28.rev02.operational import Bus, Cabinet

def case():
    c = OperationalCase(
        buses=(Bus("A",50,100,10,100,(0,0),(True,True),50),),
        cabinets=(Cabinet("C",150,2,("A",)),),
        base_load_kw=(80,80),pv_pu=(0,0),tariff_brl_kwh=(1,1))
    return CHPCase(c, CHPParameters(.4,.2,.01,(True,True)),1000)

def test_m6_real_milp_end_to_end():
    r = optimize_chp_synthetic(case(), population=4, generations=1)
    assert r["status"] == "PASS_SYNTHETIC_M6"
    assert r["nondominated"]
    assert all(x["f2_kw"] <= 2500 + 1e-6 for x in r["nondominated"])

def test_m6_chp_gene_varies():
    r = optimize_chp_synthetic(case(), population=4, generations=1)
    assert len(r["chp_values_evaluated_kw"]) > 1

def test_m6_all_infeasible_not_success():
    def reject(design, case):
        return {"status": "INFEASIBLE_MILP", "reason": "synthetic"}
    r = optimize_chp_synthetic(case(), evaluator=reject)
    assert r["status"] == "NO_FEASIBLE_SOLUTION"
    assert r["nondominated"] == []

def test_m6_costs_and_f2_from_evaluator():
    def evaluator(design, case):
        return {"status": "PASS_SYNTHETIC_M5", "design": design,
                "f1_brl_per_pkm": 1+design["chp_kw"]/1000,
                "f2_kw": 1000-design["chp_kw"]}
    r = optimize_chp_synthetic(case(), evaluator=evaluator)
    assert r["status"] == "PASS_SYNTHETIC_M6"
    assert all(x["f1_brl_per_pkm"] > 1 and x["f2_kw"] < 1000
               for x in r["nondominated"])

def test_m6_invalid_chp_bounds():
    with pytest.raises(ValueError):
        optimize_chp_synthetic(case(), bounds={
            "pv_kw":(0,100), "bess_kwh":(20,200),
            "pcs_fraction":(0,.55), "chp_kw":(-1,150)})
