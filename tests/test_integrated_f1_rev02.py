import pytest
from d28.economics.integrated_f1_rev02 import (
    AnnualRecord, COST_KEYS, PendingEvidence, evaluate_integrated_f1,
)

def record(t, *, missing=None, feasible=True, pkm=None):
    c = {k: 0.0 for k in COST_KEYS}
    if t == 0:
        c['frota_capex'] = 100.0
    else:
        c['energia_eletrica'] = 20.0
        c['residual_frota'] = 5.0
    if missing:
        c[missing] = None
    return AnnualRecord(t, 0.0 if t == 0 else (100.0 if pkm is None else pkm), c,
                        True, feasible, {k: 'TESTE_SINTETICO_NAO_HOMOLOGADO' for k in COST_KEYS})

def test_integrated_f1_math_and_residual():
    result = evaluate_integrated_f1('BAU', [record(0), record(1)], 0.0, 1, 1000.0)
    assert result['f1_integrado_brl_per_pkm'] == pytest.approx(1.15)
    assert result['f2_peak_pcc_kw'] == 1000.0

def test_missing_cost_blocks():
    with pytest.raises(PendingEvidence, match='custos pendentes'):
        evaluate_integrated_f1('BAU', [record(0), record(1, missing='combustivel_gas')], 0.1, 1, 100.0)

def test_infeasible_blocks():
    with pytest.raises(PendingEvidence, match='despacho'):
        evaluate_integrated_f1('Realista', [record(0), record(1, feasible=False)], 0.1, 1, 100.0)

def test_pcc_cap_blocks():
    with pytest.raises(PendingEvidence, match='PCC'):
        evaluate_integrated_f1('Cenario_1', [record(0), record(1)], 0.1, 1, 2501.0, 2500.0)

def test_no_fake_f2():
    with pytest.raises(PendingEvidence, match='F2'):
        evaluate_integrated_f1('BAU', [record(0), record(1)], 0.1, 1)

def test_missing_provenance_blocks():
    r = record(1)
    r.provenance.pop('frota_capex')
    with pytest.raises(PendingEvidence, match='evidência'):
        evaluate_integrated_f1('BAU', [record(0), r], 0.1, 1, 100.0)
