"""Contrato de avaliação NSGA-II <-> MILP; integração R0 em estágio controlado.

F1 e F3 exigem funções de contabilidade fornecidas pelo projeto; nenhum
fator ambiental ou PKM é inventado. R1/R2/R3 permanecem não conectadas.
"""
from dataclasses import dataclass
from typing import Callable
import math

@dataclass(frozen=True)
class DesignR0:
    pv_kwp: float
    bess_kwh: float
    pcs_kw: float

@dataclass(frozen=True)
class Evaluation:
    feasible: bool
    objectives: tuple[float, float, float] | None
    reason: str
    audit: dict

def evaluate_r0(design: DesignR0, *, load_kw, pv_pu, months,
                economics, annual_pkm: float | None,
                lifecycle_kgco2e: Callable[[DesignR0, dict], float] | None,
                solver_name="appsi_highs", dt_hours=0.25):
    """Executa um MILP econômico e devolve [F1,F2,F3] somente se íntegros.

    Exige 12 meses reais para o adaptador econômico M3.1; não anualiza
    artificialmente quatro intervalos ou os 70 dias sintéticos.
    """
    if annual_pkm is None or annual_pkm <= 0 or lifecycle_kgco2e is None:
        return Evaluation(False, None, "PKM ou inventário ACV ausente", {})
    if not all(math.isfinite(v) and v >= 0 for v in
               (design.pv_kwp, design.bess_kwh, design.pcs_kw)):
        return Evaluation(False, None, "Dimensionamento inválido", {})
    try:
        import pyomo.environ as p
        from d28.dispatch.milp import build_r0_milp
        from d28.economics.milp_adapter import attach_economic_objective
        from d28.economics.f1 import present_value
        model = build_r0_milp(
            load_kw, pv_pu, design.pv_kwp, design.bess_kwh, design.pcs_kw,
            dt_hours=dt_hours, terminal_policy="cyclic",
            pcc_cap_kw=economics.pcc_import_limit_kw,
            pv_capacity_max_kwp=economics.pv_capacity_max_kwp)
        attach_economic_objective(
            model, economics, pv_kwp=design.pv_kwp,
            bess_kwh=design.bess_kwh, pcs_kw=design.pcs_kw,
            months=months, dt_hours=dt_hours, annual_pkm=annual_pkm)
        solver = p.SolverFactory(solver_name)
        if not solver.available(exception_flag=False):
            return Evaluation(False, None, "Solver indisponível", {})
        results = solver.solve(model, load_solutions=False)
        term = results.solver.termination_condition
        if term != p.TerminationCondition.optimal:
            return Evaluation(False, None, f"MILP não ótimo: {term}", {})
        model.solutions.load_from(results)
        grid = [float(p.value(model.grid[t])) for t in model.T]
        pv_cost = float(p.value(model.m31_pv_cost_brl))
        f1 = float(p.value(model.m31_f1_brl_per_pkm))
        f2 = max(grid)
        audit = {
            "route": "R0", "grid_kw": grid, "pv_cost_brl": pv_cost,
            "annual_pkm": annual_pkm, "solver": solver_name,
            "economic_scope": "M3.1 annual, repeated over horizon",
            "model_scope": "R0 aggregated only"}
        ghg = float(lifecycle_kgco2e(design, audit))
        if not math.isfinite(ghg) or ghg < 0:
            return Evaluation(False, None, "Inventário ACV inválido", audit)
        f3 = ghg / (annual_pkm * economics.horizon_years)
        if not all(math.isfinite(v) for v in (f1, f2, f3)):
            return Evaluation(False, None, "Objetivos não finitos", audit)
        audit["lifecycle_kgco2e"] = ghg
        return Evaluation(True, (f1, f2, f3), "", audit)
    except (ValueError, ImportError, RuntimeError) as exc:
        return Evaluation(False, None, f"Falha de avaliação: {exc}", {})

def evaluate_population(population, evaluator: Callable):
    """Loop independente de biblioteca: o NSGA-II chama este avaliador
    a cada geração. Inviáveis não recebem objetivos artificiais."""
    return [evaluator(candidate) for candidate in population]

def to_pymoo_result(evaluations):
    """Adaptador somente para população totalmente factível e auditada."""
    if not all(e.feasible and e.objectives is not None for e in evaluations):
        raise ValueError("População contém avaliações inviáveis/incompletas; "
                         "tratar restrições antes de enviar ao pymoo")
    return [list(e.objectives) for e in evaluations]
