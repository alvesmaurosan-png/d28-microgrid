import pytest
from d28.economics.integrated_f1_rev02 import AnnualRecord, COST_KEYS
from d28.economics.milp_f1_adapter_rev02 import CertifiedDispatch
from d28.optimization.nsga2_scenario_bridge_rev02_3 import (
    ScenarioContract, evaluate_design_rev02_3, nsga2_evaluation_rev02_3,
    make_pymoo_problem_rev02_3,
)

CONTRACT = ScenarioContract('BAU', 0.0, 1, 20.0, 'SINTETICO_NAO_HOMOLOGADO')

def dispatch(cid, design, contract):
    return CertifiedDispatch('TerminationCondition.optimal', [8., 15., 9., 12.], 4, 'MILP_SINTETICO')

def economics(cid, design, contract):
    records = []
    for t in (0, 1):
        costs = {k: 0.0 for k in COST_KEYS}
        costs['frota_capex' if t == 0 else 'energia_eletrica'] = 100.0 if t == 0 else 20.0
        records.append(AnnualRecord(t, 0.0 if t == 0 else 100.0, costs, True, True,
                                    {k: 'SINTETICO' for k in COST_KEYS}))
    return records

def run(dp=dispatch, ep=economics, contract=CONTRACT):
    return evaluate_design_rev02_3(candidate_id='test', design={'pv_kwp': 10.0},
                                   contract=contract, dispatch_provider=dp,
                                   economics_provider=ep)

def test_fluxo_integrado():
    r = run()
    assert r['status'] == 'EVALUATED_CONDITIONAL'
    assert r['f1_integrado_brl_per_pkm'] == pytest.approx(1.2)
    assert r['f2_peak_pcc_kw'] == 15

def test_mapeamento_factivel():
    v = nsga2_evaluation_rev02_3(run())
    assert v['F'] == pytest.approx([1.2, 15])
    assert v['G'] == [0.0]

def test_milp_inviavel_bloqueia():
    def infeasible(*args):
        return CertifiedDispatch('TerminationCondition.infeasible', [], 4, 'MILP')
    r = run(dp=infeasible)
    assert r['status'] == 'BLOCKED'
    assert r['f1_integrado_brl_per_pkm'] is None
    assert nsga2_evaluation_rev02_3(r)['G'] == [1.0]

def test_economia_pendente_bloqueia():
    def missing(*args):
        rows = economics(*args)
        costs = dict(rows[1].costs_brl)
        costs['arla'] = None
        return [rows[0], AnnualRecord(1, 100.0, costs, True, True, rows[1].provenance)]
    assert run(ep=missing)['status'] == 'BLOCKED'

def test_provedor_lanca_erro_bloqueia():
    def broken(*args):
        raise RuntimeError('Solver falhou')
    assert 'Solver falhou' in run(dp=broken)['error']

def test_pcc_excedido_bloqueia():
    assert run(contract=ScenarioContract('BAU', 0., 1, 10., 'SINTETICO'))['status'] == 'BLOCKED'

def test_erro_no_dimensionamento_impede_provedor():
    called = []
    def provider(*args):
        called.append(True)
        return dispatch(*args)
    r = evaluate_design_rev02_3(candidate_id='x', design={'pv_kwp': -1},
        contract=CONTRACT, dispatch_provider=provider, economics_provider=economics)
    assert r['status'] == 'BLOCKED' and not called

def test_pymoo_elementwise():
    pytest.importorskip("pymoo")
    p = make_pymoo_problem_rev02_3(variable_names=['pv_kwp'], lower_bounds=[0],
        upper_bounds=[100], contract=CONTRACT, dispatch_provider=dispatch,
        economics_provider=economics)
    out = {}
    p._evaluate([10.0], out)
    assert out['F'] == pytest.approx([1.2, 15])
    assert out['G'] == [0.0]
    assert len(p.audit_history) == 1

def test_pymoo_bloqueado_nao_vira_objetivo_cientifico():
    pytest.importorskip("pymoo")
    def infeasible(*args):
        return CertifiedDispatch('infeasible', [], 4, 'MILP')
    p = make_pymoo_problem_rev02_3(variable_names=['pv_kwp'], lower_bounds=[0],
        upper_bounds=[100], contract=CONTRACT, dispatch_provider=infeasible,
        economics_provider=economics)
    out = {}
    p._evaluate([10.], out)
    assert out['G'] == [1.0]
    assert p.audit_history[0]['f1_integrado_brl_per_pkm'] is None

def test_domino_invalido():
    with pytest.raises(ValueError):
        make_pymoo_problem_rev02_3(variable_names=['x', 'x'], lower_bounds=[0, 0],
            upper_bounds=[1, 1], contract=CONTRACT, dispatch_provider=dispatch,
            economics_provider=economics)

def test_placeholder_nao_cientifico():
    v = nsga2_evaluation_rev02_3({'status': 'BLOCKED'})
    assert v['G'] == [1.0]
    assert v['scientific_result']['status'] == 'BLOCKED'
