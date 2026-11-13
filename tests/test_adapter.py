import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d28.optimization.d28_adapter_f1f2_nsga2 import evaluate_design


def test_fail_closed_pending_contract():
    called = []
    def never(*args):
        called.append(True)
        raise AssertionError('MILP must not run')
    r = evaluate_design('R0', {'pv_kw': 100}, contract={'status':'PENDING_RESEARCHER_APPROVAL'},
        evidence_approved=False, provenance=None, solve_annual_economic=never, reconcile_annual=never)
    assert not r.feasible and r.status == 'ANNUAL_CONTRACT_BLOCKED' and not called


def test_invalid_route():
    r = evaluate_design('R9', {}, contract={}, evidence_approved=False, provenance=None,
                        solve_annual_economic=None, reconcile_annual=None)
    assert not r.feasible and r.status == 'INVALID_ROUTE'

