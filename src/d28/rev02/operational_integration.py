"""REV02.1 M4: acoplamento sintético do despacho individual ao NSGA-II.

Não altera o avaliador REV02 original. Não constitui resultado científico D28.
"""
from dataclasses import dataclass
from math import isfinite

from .contracts import Scenario, contract
from .economics import IntegratedCosts
from .integration import annuity_factor
from .nsga2 import run
from .operational import build_operational_milp, solve_operational_milp


@dataclass(frozen=True)
class OperationalCase:
    buses: tuple
    cabinets: tuple
    base_load_kw: tuple
    pv_pu: tuple
    tariff_brl_kwh: tuple
    scenario: Scenario = Scenario.C1
    year: int = 2026
    dt_hours: float = 1.
    annual_pkm: float = 100_000_000.
    years: int = 12
    discount_rate: float = .08
    annualization_scale: float = 1095.
    pv_capex_brl_kw: float = 3000.
    bess_capex_brl_kwh: float = 1500.
    pcs_capex_brl_kw: float = 900.
    fleet_present_brl: float = 0.
    annual_operations_brl: float = 0.


def evaluate_operational_design(design, case: OperationalCase, *,
                                solve=solve_operational_milp):
    """Avalia candidato via MILP individual; falhas não recebem objetivos fictícios."""
    spec = contract(case.scenario, case.year)
    if spec.scenario != Scenario.C1:
        raise NotImplementedError("M4 demonstrativo restrito ao Cenario 1")
    if float(design.get("chp_kw", 0)) != 0:
        raise NotImplementedError("CHP ainda nao integrado")
    pv = float(design.get("pv_kw", 0))
    bess = float(design.get("bess_kwh", 0))
    pcs = float(design.get("pcs_kw", 0))
    if any(not isfinite(v) or v < 0 for v in (pv,bess,pcs)):
        raise ValueError("Capacidades invalidas")
    if pcs > .55*bess + 1e-8:
        return {"status":"INFEASIBLE_DESIGN","reason":"C_RATE","design":dict(design)}
    n = len(case.base_load_kw)
    if not n or len(case.pv_pu) != n or len(case.tariff_brl_kwh) != n:
        raise ValueError("Series incompatíveis")
    if case.annual_pkm <= 0 or case.annualization_scale <= 0:
        raise ValueError("PKM ou escala invalidos")
    if any(not isfinite(v) or v < 0 for v in (
        case.pv_capex_brl_kw, case.bess_capex_brl_kwh,
        case.pcs_capex_brl_kw, case.fleet_present_brl,
        case.annual_operations_brl)):
        raise ValueError("Custos invalidos")
    m = build_operational_milp(
        buses=case.buses, cabinets=case.cabinets,
        base_load_kw=case.base_load_kw, pv_pu=case.pv_pu,
        tariff_brl_kwh=case.tariff_brl_kwh,
        dt_hours=case.dt_hours, pcc_cap_kw=spec.pcc_limit_kw,
        pv_kw=pv, bess_kwh=bess, pcs_kw=pcs)
    solved = solve(m)
    if solved["status"] != "PASS_SYNTHETIC_OPERATIONAL":
        return {"status":"INFEASIBLE_MILP",
                "reason":solved.get("termination", solved["status"]),
                "design":dict(design)}
    factor = annuity_factor(case.discount_rate, case.years)
    cost = IntegratedCosts(
        fleet_brl=case.fleet_present_brl,
        infrastructure_brl=pv*case.pv_capex_brl_kw
            + bess*case.bess_capex_brl_kwh + pcs*case.pcs_capex_brl_kw,
        grid_reinforcement_brl=0.,
        energy_brl=solved["objective_brl"]*case.annualization_scale*factor,
        operations_brl=case.annual_operations_brl*factor,
        residual_brl=0.,
        discounted_pkm=case.annual_pkm*factor)
    return {
        "status":"PASS_SYNTHETIC_OPERATIONAL_INTEGRATION",
        "design":dict(design),
        "f1_brl_per_pkm":cost.f1_brl_per_pkm(),
        "f2_kw":solved["f2_kw"],
        "costs":vars(cost),
        "operational":solved,
        "classification":"SYNTHETIC_M4_NOT_D28_SCIENTIFIC_RESULT"}


def optimize_operational_synthetic(case: OperationalCase, *,
                                   population=4, generations=1, seed=42,
                                   evaluator=evaluate_operational_design):
    """NSGA-II existente; somente projetos factíveis entram na fronteira."""
    if Scenario(case.scenario) != Scenario.C1:
        raise NotImplementedError("M4 restrito ao Cenario 1")
    bounds = {"pv_kw":(0.,100.), "bess_kwh":(20.,200.),
              "pcs_fraction":(0.,.55)}
    evaluations = {}
    def decode(g):
        return {"pv_kw":g["pv_kw"],"bess_kwh":g["bess_kwh"],
                "pcs_kw":g["bess_kwh"]*g["pcs_fraction"],"chp_kw":0.}
    def key(d):
        return tuple(round(d[k], 8) for k in ("pv_kw","bess_kwh","pcs_kw"))
    def objective(g):
        d = decode(g)
        k = key(d)
        if k not in evaluations:
            evaluations[k] = evaluator(d,case)
        v = evaluations[k]
        if v["status"] != "PASS_SYNTHETIC_OPERATIONAL_INTEGRATION":
            return None
        return (v["f1_brl_per_pkm"],v["f2_kw"])
    result = run(objective,bounds,population=population,
                 generations=generations,seed=seed)
    nondominated = []
    for i in result["nondominated_indices"]:
        k = key(decode(result["population"][i]))
        v = evaluations[k]
        if v["status"] == "PASS_SYNTHETIC_OPERATIONAL_INTEGRATION":
            nondominated.append(v)
    return {
        "status":"PASS_SYNTHETIC_M4" if nondominated else "NO_FEASIBLE_SOLUTION",
        "evaluations":len(evaluations),
        "nondominated":nondominated,
        "infeasible_evaluations":sum(
            v["status"] != "PASS_SYNTHETIC_OPERATIONAL_INTEGRATION"
            for v in evaluations.values()),
        "classification":"SYNTHETIC_M4_NOT_D28_SCIENTIFIC_RESULT"}
