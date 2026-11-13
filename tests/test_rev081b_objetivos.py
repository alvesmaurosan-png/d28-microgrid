import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/integrar_objetivos_rev081b.py'
spec=importlib.util.spec_from_file_location('bridge',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixtures():
    solver={'status':'OPTIMAL','experiment':'R0_ANNUAL_A_E100','grid_energy_kwh':100.,'grid_peak_kw':20.}
    rev04={'case':'R0_A_E100','dispatch':{'grid_import_kwh_year':100.},
           'F1_components':{'conditional_initial_capex_brl':1000.,'conditional_fixed_opex_brl_year':10.,'energy_purchase_flat_tariff_exploratory_brl_year':75.},
           'F3_components':{'conditional_grid_operational_emissions_tco2e_year':.01}}
    rev06={'case':'R0_A_E100','annual':{'grid_import_kwh':100.,'physical_peak_kw':20.}}
    return solver,rev04,rev06,{}

def test_without_contract_no_fake_objectives():
    a=m.integrate(*fixtures())
    assert a['F1_brl_per_pkm'] is None and a['F3_kgco2e_per_pkm'] is None
    assert a['physical']['F2_physical_kw']==20.
    assert not a['scientific_pareto_eligible']

def test_contract_20_years_computes_conditional_vector():
    contract={'cf0_brl':1000,'annual_cashflows_brl':[100]*20,'annual_pkm':[1000]*20,
              'discount_rate_real':.12,'ghg_components_kgco2e':{k:100 for k in m.BUCKETS},
              'factor_evidence':{**{k:'TEST_ONLY' for k in m.REQUIRED},'boundary_nonoverlap_documented':True}}
    a=m.integrate(*fixtures(),contract=contract)
    assert len(a['conditional_objective_vector'])==3
    assert a['F3_kgco2e_per_pkm']==600/20000
    assert not a['scientific_pareto_eligible']

def test_missing_lca_remains_blocked():
    contract={'cf0_brl':1000,'annual_cashflows_brl':[100]*20,'annual_pkm':[1000]*20,
              'discount_rate_real':.12,'ghg_components_kgco2e':{k:100 for k in m.BUCKETS},
              'factor_evidence':{}}
    a=m.integrate(*fixtures(),contract=contract)
    assert a['F1_brl_per_pkm'] is not None and a['F3_kgco2e_per_pkm'] is None

def test_reject_mismatched_energy():
    a,b,c,d=fixtures();c['annual']['grid_import_kwh']=101
    try:m.integrate(a,b,c,d)
    except ValueError:pass
    else:raise AssertionError('Divergência não detectada')
