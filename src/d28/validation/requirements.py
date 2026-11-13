"""PC-REV08: fail-closed eligibility checks; no model/parameter mutation.

This module validates declarations, not physical feasibility or scientific approval.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

ARCHITECTURES = {
    'R0': frozenset({'grid', 'PV', 'BESS', 'charging'}),
    'R1': frozenset({'grid', 'PV', 'BESS', 'charging', 'natural_gas_CHP'}),
    'R2': frozenset({'grid', 'PV', 'BESS', 'charging', 'biogas_CHP'}),
    'R3': frozenset({'grid', 'PV', 'BESS', 'charging', 'natural_gas_CHP', 'CGOB'}),
}
SCENARIOS = {'E100': (2026, 100), 'E200': (2026, 200),
             'E300': (2026, 300), 'E375': (2038, 375), 'E450': (2050, 450)}
BLOCKS = tuple(f'B{i:02d}' for i in range(1, 8))

class EligibilityError(ValueError):
    """Missing or inconsistent evidence for the requested scientific claim."""

@dataclass(frozen=True)
class Eligibility:
    architecture_id: str
    scenario_id: str
    reference_year: int
    bev_count: int
    mode: str
    eligible: bool
    reasons: tuple[str, ...]


def validate_experiment(*, architecture_id: str, scenario_id: str,
                        reference_year: int, mode: str,
                        block_status: Mapping[str, str],
                        objective_status: Mapping[str, str],
                        temporal_scope_id: str,
                        economic_horizon_years: int = 20) -> Eligibility:
    """Validate a declared experiment; never infer approval from missing status.

    mode='development' permits an exploratory label only, not scientific approval.
    mode='definitive' requires every B01..B07 RESOLVED and F1..F3 VALIDATED.
    This deliberately conservative gate may be refined only by an approved
    architecture-specific decision recorded under PC-REV08.
    """
    if architecture_id not in ARCHITECTURES:
        raise EligibilityError(f'Unknown architecture: {architecture_id}')
    if scenario_id not in SCENARIOS:
        raise EligibilityError(f'Unknown scenario: {scenario_id}')
    year, bev = SCENARIOS[scenario_id]
    if type(reference_year) is not int or reference_year != year:
        raise EligibilityError(f'{scenario_id} requires reference_year={year}')
    if mode not in ('development', 'definitive'):
        raise EligibilityError('mode must be development or definitive')
    if not isinstance(temporal_scope_id, str) or not temporal_scope_id.strip():
        raise EligibilityError('temporal_scope_id is required')
    if type(economic_horizon_years) is not int or economic_horizon_years != 20:
        raise EligibilityError('Current protocol requires 20 economic years')
    if not isinstance(block_status, Mapping) or not isinstance(objective_status, Mapping):
        raise EligibilityError('block_status and objective_status must be mappings')
    reasons = []
    if mode == 'development':
        reasons.append('DEVELOPMENT_ONLY_NOT_SCIENTIFICALLY_HOMOLOGATED')
    else:
        for block in BLOCKS:
            if block_status.get(block) != 'RESOLVED':
                reasons.append(f'{block}_NOT_RESOLVED')
        for objective in ('F1', 'F2', 'F3'):
            if objective_status.get(objective) != 'VALIDATED':
                reasons.append(f'{objective}_NOT_VALIDATED')
    return Eligibility(architecture_id, scenario_id, year, bev, mode,
                       not reasons, tuple(reasons))


def require_numeric_factors(factors: Mapping[str, object], required: tuple[str, ...]) -> None:
    """Reject absent, non-finite, negative or nonnumeric factors; zero is explicit only."""
    import math
    if not isinstance(factors, Mapping):
        raise EligibilityError('factors must be a mapping')
    for name in required:
        value = factors.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EligibilityError(f'{name}: missing or nonnumeric factor')
        if not math.isfinite(value) or value < 0:
            raise EligibilityError(f'{name}: nonfinite or negative factor')
