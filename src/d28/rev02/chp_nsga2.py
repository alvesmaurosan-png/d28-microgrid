"""REV02.1 M6: busca NSGA-II sobre PV, BESS, PCS e CHP.

Somente Cenário 1 sintético. MILP M5 é o avaliador padrão.
Nenhuma parametrização científica D28 é homologada neste módulo.
"""
from math import isfinite
from .contracts import Scenario
from .nsga2 import run
from .chp_integration import evaluate_chp_design

SUCCESS = "PASS_SYNTHETIC_M5"

def optimize_chp_synthetic(case, *, bounds=None, population=4,
                           generations=1, seed=42, evaluator=None):
    if Scenario(case.operational.scenario) != Scenario.C1:
        raise NotImplementedError("M6: somente Cenário 1 sintético")
    if bounds is None:
        bounds = {
            "pv_kw": (0., 100.),
            "bess_kwh": (20., 200.),
            "pcs_fraction": (0., .55),
            "chp_kw": (0., 150.),
        }
    if set(bounds) != {"pv_kw", "bess_kwh", "pcs_fraction", "chp_kw"}:
        raise ValueError("M6 exige os quatro genes esperados")
    if not all(
        len(v) == 2 and all(isfinite(float(z)) for z in v)
        and 0 <= float(v[0]) < float(v[1])
        for v in bounds.values()
    ):
        raise ValueError("Limites de dimensionamento inválidos")
    if float(bounds["pcs_fraction"][1]) > .55:
        raise ValueError("C-rate PCS/BESS excede limite M5")
    if evaluator is None:
        evaluator = evaluate_chp_design

    records = {}
    def decode(g):
        return {
            "pv_kw": float(g["pv_kw"]),
            "bess_kwh": float(g["bess_kwh"]),
            "pcs_kw": float(g["bess_kwh"])*float(g["pcs_fraction"]),
            "chp_kw": float(g["chp_kw"]),
        }
    def key(d):
        return tuple(round(d[k], 9) for k in
                     ("pv_kw", "bess_kwh", "pcs_kw", "chp_kw"))
    def score(g):
        design = decode(g)
        k = key(design)
        if k not in records:
            records[k] = evaluator(design, case)
        result = records[k]
        if result["status"] != SUCCESS:
            return None
        f1, f2 = result["f1_brl_per_pkm"], result["f2_kw"]
        if not all(isfinite(float(x)) for x in (f1, f2)):
            return None
        return (float(f1), float(f2))

    ga = run(score, bounds, population=population,
             generations=generations, seed=seed)
    feasible = []
    for i in ga["nondominated_indices"]:
        design = decode(ga["population"][i])
        result = records[key(design)]
        if result["status"] == SUCCESS and all(
            isfinite(float(result[k]))
            for k in ("f1_brl_per_pkm", "f2_kw")
        ):
            feasible.append(result)
    # Deduplicação de soluções repetidas na população final.
    unique = {key(x["design"]): x for x in feasible}
    return {
        "status": "PASS_SYNTHETIC_M6" if unique else "NO_FEASIBLE_SOLUTION",
        "nondominated": list(unique.values()),
        "evaluations": len(records),
        "infeasible_evaluations": sum(
            r["status"] != SUCCESS for r in records.values()),
        "chp_values_evaluated_kw": sorted(set(
            k[3] for k in records
        )),
        "classification": "SYNTHETIC_M6_NOT_D28_SCIENTIFIC_RESULT",
    }
