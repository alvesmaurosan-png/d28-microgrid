import json
from pathlib import Path
import pytest
from d28.optimization.annual_f1_f2_connector_rev06 import evaluate_annual, make_annual_problem

CONTRACT = Path(__file__).resolve().parents[1] / 'contrato_anual.json'

def test_real_contract_remains_blocked_before_factory():
    contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
    def forbidden(*args):
        raise AssertionError('Solver/factory must never be called')
    result=evaluate_annual('R0', {'pv_kw':100,'bess_kwh':500,'pcs_kw':100},
                           contract=contract,evidence_factory=forbidden)
    assert not result.feasible and result.objectives is None
    assert result.status=='ANNUAL_CONTRACT_BLOCKED'

def test_nsga2_is_blocked_before_importing_pymoo():
    contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
    with pytest.raises(ValueError,match='ANNUAL_CONTRACT_BLOCKED'):
        make_annual_problem('R0',{'pv_kw':(0,100)},contract=contract,
                            evidence_factory=lambda *_: None)
