"""Despacho lexicografico anual, independente da arquitetura.

Etapa 1: minimizar pico de importacao.
Etapa 2: minimizar energia importada, preservando o pico otimo.
Nao estabelece homologacao cientifica.
"""
from dataclasses import dataclass
import math
import pyomo.environ as p


@dataclass(frozen=True)
class LexicographicResult:
    optimal: bool
    reason: str
    peak_kw: float | None
    grid_energy_kwh: float | None
    grid_kw: tuple[float, ...] | None
    primary_termination: str
    secondary_termination: str
    peak_preservation_residual_kw: float | None


def solve_annual_lexicographic(
    model,
    *,
    dt_hours: float = 0.25,
    peak_tolerance_kw: float = 1e-5,
    solver_name: str = "appsi_highs",
) -> LexicographicResult:
    if not math.isfinite(dt_hours) or dt_hours <= 0:
        raise ValueError("dt_hours invalido")
    if not math.isfinite(peak_tolerance_kw) or peak_tolerance_kw < 0:
        raise ValueError("peak_tolerance_kw invalida")
    if not hasattr(model, "grid") or not hasattr(model, "T"):
        raise ValueError("Modelo sem grid ou indice temporal T")

    times = tuple(model.T)
    if not times:
        raise ValueError("Horizonte temporal vazio")

    for obj in model.component_data_objects(p.Objective, active=True):
        obj.deactivate()

    if hasattr(model, "_d28_lex_peak"):
        raise ValueError("Despacho lexicografico ja instalado no modelo")

    model._d28_lex_peak = p.Var(domain=p.NonNegativeReals)
    model._d28_lex_peak_limit = p.Constraint(
        model.T,
        rule=lambda m, t: m.grid[t] <= m._d28_lex_peak,
    )
    model._d28_lex_primary = p.Objective(
        expr=model._d28_lex_peak,
        sense=p.minimize,
    )

    solver = p.SolverFactory(solver_name)
    if not solver.available():
        raise RuntimeError("Solucionador indisponivel")

    first = solver.solve(model)
    primary_status = str(first.solver.termination_condition)

    if first.solver.termination_condition != p.TerminationCondition.optimal:
        return LexicographicResult(
            False, "PRIMARY_NOT_OPTIMAL",
            None, None, None, primary_status, "NOT_RUN", None,
        )

    optimal_peak = float(p.value(model._d28_lex_peak))

    model._d28_lex_primary.deactivate()
    model._d28_lex_peak_lock = p.Constraint(
        expr=model._d28_lex_peak <= optimal_peak + peak_tolerance_kw
    )
    model._d28_lex_secondary = p.Objective(
        expr=dt_hours * sum(model.grid[t] for t in times),
        sense=p.minimize,
    )

    second = solver.solve(model)
    secondary_status = str(second.solver.termination_condition)

    if second.solver.termination_condition != p.TerminationCondition.optimal:
        return LexicographicResult(
            False, "SECONDARY_NOT_OPTIMAL",
            None, None, None,
            primary_status, secondary_status, None,
        )

    grid = tuple(float(p.value(model.grid[t])) for t in times)

    if any(not math.isfinite(v) or v < -1e-7 for v in grid):
        raise RuntimeError("Importacao de rede invalida")

    peak = max(grid)
    residual = max(0.0, peak - optimal_peak)

    if residual > peak_tolerance_kw + 1e-6:
        raise RuntimeError("Pico otimo nao preservado")

    return LexicographicResult(
        True,
        "",
        peak,
        dt_hours * sum(grid),
        grid,
        primary_status,
        secondary_status,
        residual,
    )
