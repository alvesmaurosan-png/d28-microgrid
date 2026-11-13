import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('rev081c',ROOT/'scripts/integrar_objetivos_rev081c.py')
M=importlib.util.module_from_spec(S)
S.loader.exec_module(M)


def fixture():
    records=M.master_records(ROOT/'data/raw/parametros/Base_Mestre_D28_PC_REV07_REV02.xlsx')
    cfg=json.loads((ROOT/'config/economics/r0_f1_exploratory_2026.json').read_text())
    candidate={'design':{'pv_kw':205.4806088017267,'bess_kwh':28272.75736597176,'pcs_kw':4996.651562474392},
               'grid_energy_kwh':7252591.481003239,'grid_peak_kw':2500.0000000000027}
    return records,cfg,candidate


def test_pkm_reproducible():
    r,_,_=fixture()
    assert M.annual_pkm_basis(r,100)['annual_pkm']==137675700


def test_cashflow_20_years():
    _,cfg,c=fixture()
    x=M.cashflows(cfg,**{'pv':c['design']['pv_kw'],'bess':c['design']['bess_kwh'],
                         'pcs':c['design']['pcs_kw'],'energy':c['grid_energy_kwh']})
    assert len(x['annual_cashflows_brl'])==20
    assert x['annual_cashflows_brl'][11]>x['annual_cashflows_brl'][10]


def test_conditional_f1_not_scientific():
    r,cfg,c=fixture()
    x=M.evaluate(c,r,cfg)
    assert 0.10<x['F1_conditional_brl_per_pkm']<0.11
    assert x['F1_brl_per_pkm'] is None
    assert x['F3_kgco2e_per_pkm'] is None
    assert not x['scientific_pareto_eligible']


def test_granular_lca():
    r,cfg,c=fixture()
    x=M.evaluate(c,r,cfg)
    assert x['lca_audit']['factors']['D11-014']['status']=='MISSING_FACTOR'
    assert x['lca_audit']['buckets']['operation']['evidence']
    assert x['lca_audit']['buckets']['eol']['kgco2e'] is None
