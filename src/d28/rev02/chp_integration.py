"""REV02.1 M5: avaliador sintético com CHP; preserva avaliador M4."""
from dataclasses import dataclass
from math import isfinite

from .chp import CHPParameters, attach_chp, solve_chp_operational
from .contracts import Scenario, contract
from .economics import IntegratedCosts
from .integration import annuity_factor
from .operational import build_operational_milp
from .operational_integration import OperationalCase


@dataclass(frozen=True)
class CHPCase:
    operational: OperationalCase
    parameters: CHPParameters
    chp_capex_brl_kw: float


def evaluate_chp_design(design, case: CHPCase, *, solve=solve_chp_operational):
    """F1 é proxy sintética; investimento CHP contabilizado uma única vez."""
    c = case.operational
    spec = contract(c.scenario, c.year)
    if spec.scenario != Scenario.C1 or not spec.local_pv_bess_chp:
        raise NotImplementedError('M5 experimental somente Cenário 1')
    pv, bess, pcs, chp = (float(design.get(k, 0.0)) for k in
                           ('pv_kw','bess_kwh','pcs_kw','chp_kw'))
    if any(not isfinite(x) or x < 0 for x in (pv,bess,pcs,chp,case.chp_capex_brl_kw)):
        raise ValueError('Capacidades ou CAPEX inválidos')
    if pcs > .55*bess + 1e-8:
        return {'status':'INFEASIBLE_DESIGN','reason':'C_RATE','design':dict(design)}
    if c.annual_pkm <= 0 or c.annualization_scale <= 0:
        raise ValueError('PKM ou escala anual inválidos')
    model = build_operational_milp(
        buses=c.buses,cabinets=c.cabinets,base_load_kw=c.base_load_kw,
        pv_pu=c.pv_pu,dt_hours=c.dt_hours,pcc_cap_kw=spec.pcc_limit_kw,
        pv_kw=pv,bess_kwh=bess,pcs_kw=pcs,tariff_brl_kwh=c.tariff_brl_kwh)
    attach_chp(model,capacity_kw=chp,parameters=case.parameters,dt_hours=c.dt_hours)
    r = solve(model)
    if r['status'] != 'PASS_SYNTHETIC_OPERATIONAL_CHP':
        return {'status':'INFEASIBLE_MILP',
                'reason':r.get('termination',r['status']),'design':dict(design)}
    factor = annuity_factor(c.discount_rate,c.years)
    costs = IntegratedCosts(
        fleet_brl=c.fleet_present_brl,
        infrastructure_brl=pv*c.pv_capex_brl_kw+bess*c.bess_capex_brl_kwh+
                           pcs*c.pcs_capex_brl_kw+chp*case.chp_capex_brl_kw,
        grid_reinforcement_brl=0.,
        energy_brl=r['objective_brl']*c.annualization_scale*factor,
        operations_brl=c.annual_operations_brl*factor,
        residual_brl=0.,discounted_pkm=c.annual_pkm*factor)
    return {'status':'PASS_SYNTHETIC_M5','design':dict(design),
            'f1_brl_per_pkm':costs.f1_brl_per_pkm(), 'f2_kw':r['f2_kw'],
            'costs':vars(costs),'operational':r,
            'classification':'SYNTHETIC_M5_NOT_D28_SCIENTIFIC_RESULT'}
