"""Contract of the real R0-R3 model builder with the existing scientific bridge.

The MILP solver is deliberately mocked: no annual dispatch or approval is inferred.
"""
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from d28.optimization.route_milp_adapter import evaluate_route_candidate
from d28.optimization.d28_scientific_bridge import nsga2_objectives

COMMON = dict(load_kw=[100.,120.,110.,90.], pv_pu=[0.,.3,.5,0.], pcc_cap_kw=2500., dt_hours=.25)
DESIGN = dict(pv_capacity_kw=100., bess_capacity_kwh=500., pcs_power_kw=200.)
CHP = dict(chp_capacity_kw=150., electrical_efficiency=.35,
           fuel_lhv_kwh_per_nm3=6., availability=[1,1,1,1])
BIOGAS = dict(production_nm3=[10.]*4, gasometer_capacity_nm3=100., initial_gas_nm3=50.)
CGOB = dict(cgob_coverage_nm3=1.)

@dataclass
class Dispatch:
    optimal: bool = True
    grid_kw: tuple = (20., 30., 10., 25.)
    peak_kw: float = 30.
    primary_termination: str = 'optimal'
    secondary_termination: str = 'optimal'
    peak_preservation_residual_kw: float = 0.

@pytest.mark.parametrize('route', ['R0','R1','R2','R3'])
def test_real_constructor_and_scientific_gate(route):
    options = dict(common=COMMON, expected_intervals=4)
    if route != 'R0':
        options['chp'] = CHP
    if route == 'R2':
        options['biogas'] = BIOGAS
    if route == 'R3':
        options['cgob'] = CGOB

    def mocked_solver(model, *, dt_hours, solver_name):
        assert len(model.T) == 4
        assert dt_hours == .25
        assert solver_name == 'appsi_highs'
        if route != 'R0': assert hasattr(model, 'chp')
        if route == 'R2': assert hasattr(model, 'gas_transition')
        if route == 'R3': assert hasattr(model, 'cgob_coverage_limit')
        return Dispatch()

    with patch('d28.optimization.route_milp_adapter.solve_annual_lexicographic', side_effect=mocked_solver) as solve:
        result = evaluate_route_candidate(route, DESIGN, **options)
    solve.assert_called_once()
    assert result.status == 'F1_PENDING'
    assert result.f2_kw == 30.
    assert result.audit['grid_energy_kwh'] == pytest.approx(21.25)
    assert result.objectives is None
    with pytest.raises(ValueError, match='SCIENTIFIC_PARETO_BLOCKED'):
        nsga2_objectives([result])

@pytest.mark.parametrize('route', ['R0','R1','R2','R3'])
def test_f3_and_approvals_still_block_pareto(route):
    options = dict(common=COMMON, expected_intervals=4, compute_f1=lambda *a: .25,
                   compute_f3=lambda *a: .08, evidence={})
    if route != 'R0': options['chp'] = CHP
    if route == 'R2': options['biogas'] = BIOGAS
    if route == 'R3': options['cgob'] = CGOB
    with patch('d28.optimization.route_milp_adapter.solve_annual_lexicographic', return_value=Dispatch()):
        result = evaluate_route_candidate(route, DESIGN, **options)
    assert result.status == 'THREE_OBJECTIVES_CONDITIONAL'
    assert result.objectives is None
    assert result.audit['missing_scientific_evidence']
