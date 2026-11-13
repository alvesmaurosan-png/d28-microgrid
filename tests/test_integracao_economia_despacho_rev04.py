import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/integrar_economia_despacho_anual_rev04.py'
spec = importlib.util.spec_from_file_location('rev04', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
CFG = json.loads((ROOT / 'config/economics/r0_f1_exploratory_2026.json').read_text(encoding='utf-8'))


def sample():
    solver = {'status': 'OPTIMAL', 'termination': 'optimal', 'experiment': 'R0_ANNUAL_A_E100',
              'grid_energy_kwh': 7252591.481003239, 'grid_peak_kw': 2500.0,
              'pv_capacity_kw': 205.4806088017267, 'bess_capacity_kwh': 28272.75736597176,
              'pcs_power_kw': 4996.651562474392}
    rev03 = {'case': 'R0_A_E100', 'classification': 'OPTIMAL_MILP_CONDITIONAL_SYNTHETIC_COUNTERFACTUAL',
             'physical_dispatch': {'grid_import_kwh_year': solver['grid_energy_kwh'], 'grid_peak_kw': 2500.0},
             'F3_components': {'conditional_grid_operational_emissions_tco2e_year': 722.3581115079226,
                               'factor_parameter_id': 'D11-017'}}
    return solver, rev03


def test_values_and_no_false_demand_billing():
    s, r = sample()
    out = module.integrate(s, r, CFG, [])
    f = out['F1_components']
    assert f['energy_purchase_flat_tariff_exploratory_brl_year'] == pytest.approx(7252591.481003239 * .75)
    assert f['monthly_demand_charge_brl_year'] is None
    assert f['time_of_use_energy_purchase_brl_year'] is None
    assert f['conditional_initial_capex_brl'] > 0
    assert out['F3_components']['conditional_grid_operational_emissions_tco2e_year'] == pytest.approx(722.3581115079226)
    assert out['F1'] is None and out['F3'] is None


def test_reject_unvalidated_solver():
    s, r = sample()
    s['status'] = 'NOT_CERTIFIED_OPTIMAL'
    with pytest.raises(ValueError):
        module.integrate(s, r, CFG, [])


def test_reject_mismatched_energy():
    s, r = sample()
    r['physical_dispatch']['grid_import_kwh_year'] += 100
    with pytest.raises(ValueError):
        module.integrate(s, r, CFG, [])
