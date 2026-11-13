import pytest
from d28.optimization.objective_integration import integrate_objectives

def test_diagnostic_preserves_f2_without_inventing_f1_f3():
    result=integrate_objectives('R2',grid_kw=[100, 160, 80],contract={'status':'PENDING'})
    assert result.f2_kw==160
    assert result.objectives is None
    assert result.status=='F2_ONLY_ANNUAL_BLOCKED'

def test_missing_contract_fails_closed():
    result=integrate_objectives('R0',grid_kw=[0, 12])
    assert result.objectives is None

def test_invalid_grid_rejected():
    with pytest.raises(ValueError):
        integrate_objectives('R1',grid_kw=[float('nan')])
    with pytest.raises(ValueError):
        integrate_objectives('R1',grid_kw=[-1])

def test_invalid_route_rejected():
    with pytest.raises(ValueError):
        integrate_objectives('R9',grid_kw=[1])
