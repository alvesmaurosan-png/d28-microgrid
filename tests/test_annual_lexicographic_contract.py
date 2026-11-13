"""Teste matematico reduzido; nao executa o cenario anual D28."""
import pytest

p = pytest.importorskip("pyomo.environ")

from d28.optimization.annual_lexicographic_dispatch import (
    solve_annual_lexicographic,
)


def test_peak_first_then_energy_with_appsi_highs():
    solver = p.SolverFactory("appsi_highs")
    if not solver.available(exception_flag=False):
        pytest.skip("appsi_highs not installed")

    m = p.ConcreteModel()
    m.T = p.RangeSet(0, 1)
    m.grid = p.Var(m.T, bounds=(0, 10))

    m.demand = p.Constraint(
        expr=sum(m.grid[t] for t in m.T) >= 8
    )

    m.original_objective = p.Objective(
        expr=sum(m.grid[t] for t in m.T)
    )

    result = solve_annual_lexicographic(
        m,
        dt_hours=0.25,
    )

    assert result.optimal, (
        result.reason,
        result.primary_termination,
        result.secondary_termination,
    )

    assert result.peak_kw == pytest.approx(4.0, abs=1e-4)
    assert result.grid_energy_kwh == pytest.approx(2.0, abs=1e-4)
    assert result.peak_preservation_residual_kw <= 1.1e-5
