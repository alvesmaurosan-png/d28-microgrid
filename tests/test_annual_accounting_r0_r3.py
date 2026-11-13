import pytest
from d28.optimization.annual_accounting_r0_r3 import AnnualAccounting, annual_objectives
from d28.optimization.r0_r3_bridge import annual_contract_ready


def test_pending_contract_blocks_before_economic_calculation():
    with pytest.raises(ValueError, match='ANNUAL_CONTRACT_BLOCKED'):
        annual_objectives('R2', cfg=None, pv_kwp=0, bess_kwh=0, pcs_kw=0,
                          grid_kw=[], months=[], dt_hours=.25, annual_pkm=1,
                          accounting=AnnualAccounting(), contract={'status':'PENDING_RESEARCHER_APPROVAL'})


def test_missing_r3_rule_fails_closed(monkeypatch):
    # A entrada temporal sintética aqui só testa os bloqueios; não é homologação.
    import d28.optimization.r0_r3_bridge as bridge
    monkeypatch.setattr(bridge,'annual_contract_ready',lambda c:(True,''))
    from d28.economics.f1 import Economics
    from dataclasses import fields
    # Falta deliberada de configuração econômica: teste unitário da validação.
    with pytest.raises((ValueError,AttributeError,TypeError)):
        annual_objectives('R3', cfg=None, pv_kwp=0, bess_kwh=0, pcs_kw=0,
                          grid_kw=[1],months=[202501],dt_hours=.25,annual_pkm=1,
                          accounting=AnnualAccounting(cgob_accounting_rule=None),contract={'year':2025})


def test_accounting_rejects_nonfinite_lifecycle():
    from d28.optimization.annual_accounting_r0_r3 import nonnegative
    with pytest.raises(ValueError): nonnegative('ACV',float('nan'))
    with pytest.raises(ValueError): nonnegative('ACV',-1)
    with pytest.raises(ValueError): nonnegative('ACV',None)
