import pytest
from d28.economics.integrated_f1_rev02 import AnnualRecord, COST_KEYS, PendingEvidence
from d28.economics.milp_f1_adapter_rev02 import CertifiedDispatch, adapt_milp_to_integrated_f1


def annual(t, *, missing=None, feasible=True):
    costs = {key: 0.0 for key in COST_KEYS}
    costs['frota_capex' if t == 0 else 'energia_eletrica'] = 100.0 if t == 0 else 20.0
    if missing:
        costs[missing] = None
    return AnnualRecord(t, 0.0 if t == 0 else 100.0, costs, True, feasible,
                        {k: 'SINTETICO_TESTE_SEM_HOMOLOGACAO' for k in COST_KEYS})


def dispatch(**changes):
    args = dict(termination_condition='TerminationCondition.optimal',
                import_pcc_kw=[10.0, 15.0, 8.0, 12.0], expected_intervals=4,
                source='SINTETICO_TESTE')
    args.update(changes)
    return CertifiedDispatch(**args)


def calc(d=None, records=None, **kwargs):
    return adapt_milp_to_integrated_f1(scenario='BAU', dispatch=d or dispatch(),
        annual_cost_and_service=records if records is not None else [annual(0), annual(1)],
        discount_rate=0.0, horizon_years=1, pcc_cap_kw=20.0, **kwargs)


def test_calculo_integrado_e_pico_efetivo():
    r = calc()
    assert r['f1_integrado_brl_per_pkm'] == pytest.approx(1.2)
    assert r['f2_peak_pcc_kw'] == 15.0
    assert r['dispatch_source'] == 'SINTETICO_TESTE'


def test_nao_otimo_bloqueado():
    with pytest.raises(PendingEvidence, match='término ótimo'):
        calc(dispatch(termination_condition='TerminationCondition.infeasible'))


def test_serie_incompleta_bloqueada():
    with pytest.raises(PendingEvidence, match='incompleta'):
        calc(dispatch(expected_intervals=5))


def test_pcc_nao_finito_bloqueado():
    with pytest.raises(PendingEvidence, match='inválida'):
        calc(dispatch(import_pcc_kw=[1.0, 2.0, float('nan'), 3.0]))


def test_limite_pcc_bloqueado():
    with pytest.raises(PendingEvidence, match='PCC'):
        calc(dispatch(import_pcc_kw=[10.0, 25.0, 8.0, 12.0]))


def test_custo_pendente_bloqueado():
    with pytest.raises(PendingEvidence, match='custos pendentes'):
        calc(records=[annual(0), annual(1, missing='combustivel_gas')])


def test_servico_nao_comprovado_bloqueado():
    with pytest.raises(PendingEvidence, match='despacho/serviço'):
        calc(records=[annual(0), annual(1, feasible=False)])
