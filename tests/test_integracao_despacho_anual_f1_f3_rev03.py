import importlib.util
from pathlib import Path
import pytest

PATH = Path(__file__).resolve().parents[1] / 'scripts/integrar_despacho_anual_f1_f3_rev03.py'
spec = importlib.util.spec_from_file_location('rev03', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    solver = {'status':'OPTIMAL','termination':'optimal','experiment':'R0_ANNUAL_A_E100', 'scenario':'E100',
              'intervals':35040,'dt_hours':.25,'grid_energy_kwh':7252591.481003239,'grid_peak_kw':2500.0000000000027,
              'pcc_kw':2500.,'soc_closure_residual_kwh':0.,'objective':'MIN_GRID_ENERGY_NOT_LEXICOGRAPHIC_F2'}
    preflight = {'status':'ANNUAL_R0_CONDITIONAL_OPTIMAL','design':'A','scenario':'E100','intervals':35040,
                 'solver_process_returncode':0,'solver_status':'OPTIMAL',
                 'solver_result_path':'results\\r0_annual_validation\\annual_A_E100.json',
                 'annual_grid_energy_kwh':7252591.481003239,'annual_grid_peak_kw':2500.0000000000027,
                 'annual_charging_ac_kwh':7267276.553322}
    annual = {'parameter_registry':{'D11-017':{'numeric_value':0.0996,'unit':'kgCO2e/kWh'}}}
    components = {'annualized_R0_R3':False}
    return solver,preflight,annual,components,[]


def test_integrates_actual_grid_not_charging_proxy():
    result=m.integrate(*fixture())
    assert result['F3_components']['conditional_grid_operational_emissions_kgco2e_year'] == pytest.approx(7252591.481003239 * .0996)
    assert result['physical_dispatch']['grid_import_kwh_year'] != result['physical_dispatch']['charging_ac_kwh_year']
    assert result['F1'] is None and result['F3'] is None


def test_rejects_nonoptimal_and_pcc_violation():
    args=list(fixture()); args[0]['status']='NOT_CERTIFIED_OPTIMAL'
    with pytest.raises(ValueError): m.integrate(*args)
    args=list(fixture()); args[0]['grid_peak_kw']=2600.; args[1]['annual_grid_peak_kw']=2600.
    with pytest.raises(ValueError): m.integrate(*args)


def test_rejects_wrong_factor():
    args=list(fixture()); args[2]['parameter_registry']['D11-017']['numeric_value']=.2
    with pytest.raises(ValueError): m.integrate(*args)
