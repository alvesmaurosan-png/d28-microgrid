import json
from pathlib import Path
import pytest
from d28.optimization.r0_r3_bridge import (
    build_architecture, annual_contract_ready, evaluate_route)

ROOT = Path(__file__).resolve().parents[1]

def test_pending_annual_contract_blocks_all_routes():
    contract = json.loads((ROOT / 'contrato_anual.json').read_text(encoding='utf-8'))
    assert not annual_contract_ready(contract)[0]
    for route in ('R0', 'R1', 'R2', 'R3'):
        result = evaluate_route(route, common={}, contract=contract)
        assert not result.feasible and result.objectives is None
        assert result.audit['gate'] == 'ANNUAL_CONTRACT_BLOCKED'

def test_incomplete_approved_map_still_blocked():
    contract = {'status':'APPROVED', 'mapping_evidence_status':'APPROVED',
                'year':2025, 'calendar_mapping_rationale':'teste',
                'source_day_for_calendar_day':{'2025-01-01':'day1'}}
    assert not annual_contract_ready(contract)[0]

def test_missing_architecture_parameters_fail_explicitly():
    with pytest.raises(ValueError, match='CHP'):
        build_architecture('R1', common={})
    with pytest.raises(ValueError, match='biogás'):
        build_architecture('R2', common={}, chp={})
    with pytest.raises(ValueError, match='CGOB'):
        build_architecture('R3', common={}, chp={})
