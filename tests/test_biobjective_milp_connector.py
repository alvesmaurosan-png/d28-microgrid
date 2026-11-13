import pytest
pytest.importorskip("pyomo.environ")
from d28.optimization.biobjective_milp_connector import ConnectorInputs, build_route_milp, evaluate_route_connected


def test_r0_constructor_real():
    m = build_route_milp('R0', {'pv_kw':10,'bess_kwh':100,'pcs_kw':20},
                         ConnectorInputs((100.,120.,110.,90.), (0.,.5,.8,0.)))
    assert len(list(m.T)) == 4
    assert hasattr(m, 'grid')


def test_r1_constructor_real():
    inputs = ConnectorInputs((100.,120.,110.,90.), (0.,.5,.8,0.), route_options={
        'chp_capacity_kw':50, 'electrical_efficiency':.35,
        'fuel_lhv_kwh_per_nm3':9.5, 'availability':[1,1,1,1]})
    m = build_route_milp('R1', {'pv_kw':10,'bess_kwh':100,'pcs_kw':20}, inputs)
    assert hasattr(m, 'chp')


def test_short_pilot_never_claims_f1():
    inputs = ConnectorInputs((100.,120.,110.,90.), (0.,.5,.8,0.))
    result = evaluate_route_connected('R0', {'pv_kw':10,'bess_kwh':100,'pcs_kw':20}, inputs)
    assert not result.feasible
    assert result.objectives is None
    assert result.status in ('PILOT_ONLY_NO_ANNUAL_F1', 'CONNECTOR_ERROR', 'MILP_NOT_OPTIMAL')
    if result.status == 'PILOT_ONLY_NO_ANNUAL_F1':
        assert result.audit['pilot_f2_kw'] >= 0
