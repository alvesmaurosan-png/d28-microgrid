import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from d28.optimization.annual_f1_f2_reconciled_rev09 import temporal_bill,annual_f1_f2_reconciled

def test_temporal_prices_and_monthly_peaks():
    b=temporal_bill([2,4,1,3],[1,2,3,4],[202501,202501,202502,202502],.25,5)
    assert b['energy_brl']==(2+8+3+12)*.25
    assert b['demand_brl']==(4+3)*5

def test_mismatched_lengths_block():
    with pytest.raises(ValueError,match='SERIES_LENGTH_MISMATCH'):
        temporal_bill([1,2],[1],[202501,202501],.25,1)

def test_negative_prices_block():
    with pytest.raises(ValueError,match='INVALID_GRID_PRICE'):
        temporal_bill([1],[-1],[202501],.25,1)

def test_contract_gate_before_solver_or_annual_series():
    with pytest.raises(ValueError,match='ANNUAL_CONTRACT_BLOCKED'):
        annual_f1_f2_reconciled('R0',cfg=None,design={},grid_kw=[],months=[],dt_hours=.25,
           prices=None,annual_pkm=0,accounting=None,contract={'status':'PENDING_RESEARCHER_APPROVAL'},
           dispatch_components={},evidence_approved=False)
