from dataclasses import replace

import pytest

from d28.economics.integrated_f1_rev02 import AnnualRecord, COST_KEYS
from d28.economics.milp_f1_adapter_rev02 import CertifiedDispatch
from d28.optimization.integrated_providers_rev02_4 import (
    IntegratedProvidersRev024, EconomicEvidence, make_operational_evidence,
)
from d28.optimization.nsga2_scenario_bridge_rev02_3 import ScenarioContract

CONTRACT = ScenarioContract('BAU', .1, 1, 500., 'fonte-economica-sintetica')
DESIGN = {'pv_kwp': 2.}


def records():
    return [AnnualRecord(t, 0. if t == 0 else 100.,
                         {k: (100. if k == 'energia_eletrica' and t == 1 else 0.) for k in COST_KEYS},
                         True, True, {k: 'SINTETICO_TESTE_ZERO_COMPROVADO' for k in COST_KEYS})
            for t in (0, 1)]


def providers(*, termination='optimal', series=(20., 30.), mismatched=False,
              energy_bound=True, omit_cost=False, tamper_digest=False):
    calls = {'solver': 0, 'economics': 0}
    def executor(cid, design, contract):
        calls['solver'] += 1
        dispatch = CertifiedDispatch(termination, series, len(series), 'milp-run-001', .25)
        op = make_operational_evidence(candidate_id=cid, scenario=contract.scenario,
                                       design=design, run_id='run-001', dispatch=dispatch)
        return replace(op, dispatch_digest='bad') if tamper_digest else op
    def builder(op, contract):
        calls['economics'] += 1
        annual = records()
        if omit_cost:
            annual[1].costs_brl.pop('energia_eletrica')
        return EconomicEvidence(op.candidate_id, op.scenario,
                                'run-outro' if mismatched else op.run_id,
                                op.dispatch_digest, annual, contract.economics_source,
                                energy_bound)
    return IntegratedProvidersRev024(executor, builder), calls


def evaluate(p):
    return p.evaluate(candidate_id='c-001', design=DESIGN, contract=CONTRACT)


def test_success_f1_f2_and_one_solve():
    p, calls = providers()
    r = evaluate(p)
    assert r['status'] == 'EVALUATED_CONDITIONAL'
    assert r['f1_integrado_brl_per_pkm'] == pytest.approx(1.)
    assert r['f2_peak_pcc_kw'] == 30.
    assert calls == {'solver': 1, 'economics': 1}
    assert r['run_id'] == 'run-001'


def test_infeasible_blocks_before_costs():
    p, calls = providers(termination='infeasible')
    assert evaluate(p)['status'] == 'BLOCKED'
    assert calls == {'solver': 1, 'economics': 0}


def test_run_mismatch_blocks():
    p, _ = providers(mismatched=True)
    assert evaluate(p)['status'] == 'BLOCKED'


def test_energy_cost_must_be_from_same_dispatch():
    p, _ = providers(energy_bound=False)
    assert evaluate(p)['status'] == 'BLOCKED'


def test_incomplete_cost_blocks():
    p, _ = providers(omit_cost=True)
    assert evaluate(p)['status'] == 'BLOCKED'


def test_digest_mismatch_blocks():
    p, _ = providers(tamper_digest=True)
    assert evaluate(p)['status'] == 'BLOCKED'


def test_pcc_violation_blocks():
    p, _ = providers(series=(20., 501.))
    assert evaluate(p)['status'] == 'BLOCKED'


def test_nsga2_constraint_not_scientific_penalty():
    p, _ = providers(termination='infeasible')
    mapped = p.evaluate_for_nsga2(candidate_id='c-001', design=DESIGN, contract=CONTRACT)
    assert mapped['G'] == [1.]
    assert mapped['scientific_result']['f1_integrado_brl_per_pkm'] is None


def test_no_cross_candidate_state():
    p, calls = providers()
    for cid in ('c-001', 'c-002'):
        assert p.evaluate(candidate_id=cid, design=DESIGN, contract=CONTRACT)['status'] == 'EVALUATED_CONDITIONAL'
    assert calls['solver'] == 2
    assert len(p.audit) == 2
