import pytest
from d28.optimization.real_milp_providers_rev02_5 import monthly_bill_from_dispatch


def test_bill_manual():
    result = monthly_bill_from_dispatch(import_pcc_kw=[10, 20, 30, 40],
        months=[202601, 202601, 202602, 202602], dt_hours=.25,
        energy_tariff_brl_kwh=1.0, demand_tariff_brl_kw_month=2.0)
    assert result['grid_energy_kwh'] == 25
    assert result['monthly_peaks_kw'] == {202601: 20, 202602: 40}
    assert result['energy_cost_brl'] == 25
    assert result['demand_cost_brl'] == 120
    assert result['total_bill_brl'] == 145
    assert result['peak_pcc_kw'] == 40

@pytest.mark.parametrize('series,months', [([], []), ([1], []), ([-1], [202601]), ([float('nan')], [202601])])
def test_invalid_series(series, months):
    with pytest.raises(ValueError):
        monthly_bill_from_dispatch(import_pcc_kw=series, months=months, dt_hours=.25,
            energy_tariff_brl_kwh=1, demand_tariff_brl_kw_month=1)

def test_invalid_tariff():
    with pytest.raises(ValueError):
        monthly_bill_from_dispatch(import_pcc_kw=[1], months=[202601], dt_hours=.25,
            energy_tariff_brl_kwh=-1, demand_tariff_brl_kw_month=1)


def test_real_highs_small_case():
    pytest.importorskip('pyomo.environ')
    from pyomo.contrib.appsi.solvers import Highs
    if not Highs().available():
        pytest.skip('HiGHS indisponível')
    from d28.optimization.real_milp_providers_rev02_5 import R0PhysicalInputs, TariffEvidence, make_r0_integrated_providers
    from d28.optimization.nsga2_scenario_bridge_rev02_3 import ScenarioContract
    physical = R0PhysicalInputs(load_kw=[10, 10, 10, 10], pv_pu=[0, 0, 0, 0],
                                months=[202601]*4, dt_hours=.25)
    tariff = TariffEvidence(1, 2, 'TARIFA_SINTETICA')
    captured = []
    def economics(op, bill, contract):
        captured.append((op, bill))
        return []  # intencional: F1 deve ser bloqueada por falta de custos e PKM
    providers = make_r0_integrated_providers(physical=physical, tariff=tariff,
                                             annual_economic_factory=economics)
    contract = ScenarioContract('BAU', .08, 1, 100, 'FONTE_SINTETICA')
    result = providers.evaluate(candidate_id='sintetico',
        design={'pv_kwp': 0., 'bess_kwh': 0., 'pcs_kw': 0.}, contract=contract)
    assert captured
    assert captured[0][1]['grid_energy_kwh'] == pytest.approx(10)
    assert captured[0][1]['peak_pcc_kw'] == pytest.approx(10)
    assert result['status'] == 'BLOCKED'  # sem custos/PKM não há F1
