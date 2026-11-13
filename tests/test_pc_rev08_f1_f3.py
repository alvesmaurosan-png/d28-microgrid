import pytest
from d28.objectives.pc_rev08_f1_f3 import f1_pc_rev08,f3_pc_rev08,REQUIRED_LCA

def test_f1_exact_20_year_pv():
    r=f1_pc_rev08(100,[10]*20,[100]*20)
    factor=sum(1/1.12**y for y in range(1,21))
    assert r['F1_brl2026_per_pkm']==pytest.approx((100+10*factor)/(100*factor))

def test_f1_rejects_daily_as_annual():
    with pytest.raises(ValueError): f1_pc_rev08(100,[10],[100])

def test_f1_rejects_missing_pkm():
    with pytest.raises(ValueError): f1_pc_rev08(0,[0]*20,[0]*20)

def test_f3_rejects_missing_factors():
    with pytest.raises(ValueError,match='D11-014'):
        f3_pc_rev08(ghg_components_kgco2e={},annual_pkm=[100]*20,factor_evidence={})

def test_f3_complete_equation():
    ev={k:'source' for k in REQUIRED_LCA}
    ev['boundary_nonoverlap_documented']='documented'
    buckets={'assets':100,'replacements':20,'operation':200,'upstream':30,'fugitive':10,'eol':40}
    r=f3_pc_rev08(ghg_components_kgco2e=buckets,annual_pkm=[100]*20,factor_evidence=ev)
    assert r['F3_kgco2e_per_pkm']==pytest.approx(.2)

def test_f3_rejects_overlap_undocumented():
    ev={k:'source' for k in REQUIRED_LCA}
    with pytest.raises(ValueError,match='OVERLAP'):
        f3_pc_rev08(ghg_components_kgco2e={k:0 for k in ('assets','replacements','operation','upstream','fugitive','eol')},annual_pkm=[100]*20,factor_evidence=ev)
