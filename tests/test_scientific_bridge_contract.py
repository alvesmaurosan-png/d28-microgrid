"""D28: isolated integration-contract tests; no annual MILP is run."""
from dataclasses import dataclass
import pytest
from d28.optimization.d28_scientific_bridge import evaluate_candidate, nsga2_objectives

APPROVALS = {
    'annual_inputs_approved': True,
    'individual_charging_validated': True,
    'economic_accounting_approved': True,
    'lifecycle_inventory_complete': True,
    'lifecycle_factors_approved': True,
    'model_physics_validated': True,
    'lexicographic_contract_approved': True,
}

@dataclass
class Dispatch:
    optimal: bool = True
    reason: str = ''
    grid_kw: tuple = (2.0, 4.0, 1.0, 3.0)
    peak_kw: float = 4.0
    primary_termination: str = 'optimal'
    secondary_termination: str = 'optimal'
    peak_preservation_residual_kw: float = 0.0


def run(dispatch=None, *, f1=None, f3=None, evidence=None, build=None, solve=None):
    return evaluate_candidate(
        'R0', {'pv_kwp': 100.0},
        build_model=build or (lambda route, design: object()),
        solve_dispatch=solve or (lambda model, dt_hours: dispatch if dispatch is not None else Dispatch()),
        compute_f1=f1,
        compute_f3=f3,
        evidence=evidence,
        expected_intervals=4,
    )


def test_f2_comes_from_grid_and_f1_missing_blocks_pareto():
    r = run()
    assert r.status == 'F1_PENDING'
    assert r.feasible and r.f2_kw == 4.0
    assert r.audit['grid_energy_kwh'] == pytest.approx(2.5)
    assert r.objectives is None
    with pytest.raises(ValueError, match='SCIENTIFIC_PARETO_BLOCKED'):
        nsga2_objectives([r])


def test_f3_missing_blocks_pareto_without_zero_substitution():
    r = run(f1=lambda *args: 0.32)
    assert r.status == 'F3_PENDING'
    assert r.f1_brl_pkm == 0.32 and r.f2_kw == 4.0
    assert r.f3_kgco2e_pkm is None
    assert r.objectives is None


def test_computed_three_objectives_remain_conditional_without_evidence():
    r = run(f1=lambda *args: 0.32, f3=lambda *args: 0.12, evidence={})
    assert r.status == 'THREE_OBJECTIVES_CONDITIONAL'
    assert not r.scientific_eligible
    assert r.objectives is None
    assert 'lifecycle_inventory_complete' in r.audit['missing_scientific_evidence']


def test_explicit_approvals_only_enable_objective_vector():
    r = run(f1=lambda *args: 0.32, f3=lambda *args: 0.12, evidence=APPROVALS)
    assert r.status == 'SCIENTIFIC_ELIGIBLE'
    assert nsga2_objectives([r]) == [[0.32, 4.0, 0.12]]


def test_infeasibility_is_not_confused_with_solver_failure():
    infeasible = run(dispatch=Dispatch(optimal=False, reason='infeasible', primary_termination='infeasible'))
    assert infeasible.status == 'INFEASIBLE'
    failure = run(solve=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('backend unavailable')))
    assert failure.status == 'SOLVER_ERROR'
    assert not failure.feasible


def test_nonoptimal_and_bad_annual_grid_are_rejected():
    nonoptimal = run(dispatch=Dispatch(optimal=False, reason='time limit'))
    assert nonoptimal.status == 'SOLVER_NOT_OPTIMAL'
    mismatch = run(dispatch=Dispatch(peak_kw=3.0))
    assert mismatch.status == 'INVALID_DISPATCH'
    short = run(dispatch=Dispatch(grid_kw=(2.0, 4.0)))
    assert short.status == 'INVALID_DISPATCH'


def test_builder_failure_is_not_solver_infeasibility():
    r = run(build=lambda *args: (_ for _ in ()).throw(RuntimeError('builder failed')))
    assert r.status == 'BUILD_ERROR'


def test_economic_failure_is_not_silently_converted_to_zero():
    r = run(f1=lambda *args: float('nan'))
    assert r.status == 'F1_INVALID'
    assert r.objectives is None


def test_environmental_failure_is_not_silently_converted_to_zero():
    r = run(f1=lambda *args: 0.32, f3=lambda *args: float('nan'))
    assert r.status == 'F3_INVALID'
    assert r.objectives is None
