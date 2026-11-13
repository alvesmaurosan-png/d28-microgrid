from d28.rev02.m7_3_physical_audit import run_synthetic


def test_m73_synthetic_physical_checks(tmp_path):
    r=run_synthetic(tmp_path)
    assert r['status']=='PASS'
    assert not r['annual_authorized']
    assert {'POWER_BALANCE','BESS','BEV_CHARGING','CHP_FUEL','PCC_2500KW','VARIABLE_BOUNDS','INTEGRALITY'} <= set(r['summary'])
    assert (tmp_path/'m7_3a_report.json').exists()
    assert (tmp_path/'m7_3a_checks.csv').exists()
