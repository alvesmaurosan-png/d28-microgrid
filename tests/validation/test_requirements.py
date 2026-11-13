import pytest
from d28.validation.requirements import (
    validate_experiment, require_numeric_factors, EligibilityError,
)

BASE = dict(architecture_id='R2', scenario_id='E375', reference_year=2038,
            temporal_scope_id='annual_15min', economic_horizon_years=20)

def test_development_never_approved():
    x = validate_experiment(**BASE, mode='development', block_status={}, objective_status={})
    assert not x.eligible and 'DEVELOPMENT_ONLY_NOT_SCIENTIFICALLY_HOMOLOGATED' in x.reasons

def test_definitive_missing_evidence_rejected():
    x = validate_experiment(**BASE, mode='definitive', block_status={}, objective_status={})
    assert not x.eligible and 'B04_NOT_RESOLVED' in x.reasons and 'F3_NOT_VALIDATED' in x.reasons

def test_definitive_all_declared_eligible_not_solver_validated():
    x = validate_experiment(**BASE, mode='definitive',
        block_status={f'B{i:02d}':'RESOLVED' for i in range(1,8)},
        objective_status={f'F{i}':'VALIDATED' for i in range(1,4)})
    assert x.eligible

def test_wrong_year_rejected():
    with pytest.raises(EligibilityError):
        validate_experiment(**{**BASE, 'reference_year':2026}, mode='development',
                            block_status={}, objective_status={})

@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), -0.1, '0', True])
def test_invalid_factor_rejected(value):
    with pytest.raises(EligibilityError):
        require_numeric_factors({'grid': value}, ('grid',))

def test_explicit_zero_is_not_missing():
    require_numeric_factors({'grid': 0.0}, ('grid',))
