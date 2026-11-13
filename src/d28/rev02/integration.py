"""Acoplamento demonstrativo NSGA-II -> Pyomo MILP -> F1/F2.

SOMENTE DADOS SINTETICOS. Nao substitui os modelos de servico, CHP, gas,
reforco de rede e contabilizacao homologada previstos no PC-REV08/REV02.
"""
from dataclasses import dataclass
from math import isfinite
from .contracts import Scenario, contract
from .dispatch import build_energy_milp, solve_energy_milp
from .economics import IntegratedCosts
from .nsga2 import run


@dataclass(frozen=True)
class SyntheticCase:
    scenario: Scenario = Scenario.C1
    year: int = 2026
    dt_hours: float = 1.0
    load_kw: tuple = (1800., 2100., 2700., 2800., 2200., 1900., 1500., 1700.)
    pv_pu: tuple = (0., 0.1, 0.4, 0.8, 0.7, 0.3, 0., 0.)
    tariff_brl_kwh: tuple = (0.7, 0.7, 1., 1., 1., 0.8, 0.7, 0.7)
    annual_pkm: float = 100_000_000.
    years: int = 12
    discount_rate: float = 0.08
    pv_capex_brl_kw: float = 3000.
    bess_capex_brl_kwh: float = 1500.
    pcs_capex_brl_kw: float = 900.
    fleet_present_brl: float = 0.
    annual_operations_brl: float = 0.
    grid_reinforcement_present_brl: float = 0.
    annualization_scale: float = 365. * 24. / 8.
    # A serie de oito horas e repetida artificialmente; nao representa a D28.


def annuity_factor(rate, years):
    if not isinstance(years, int) or years < 1 or not isfinite(rate) or rate < 0:
        raise ValueError('Horizonte/taxa invalidos')
    return sum((1. + rate) ** (-t) for t in range(1, years + 1))


def evaluate_design(design, case: SyntheticCase, *, solve=solve_energy_milp):
    """Devolve objetivos ou falha explicita; nao converte inviabilidade em PASS."""
    spec = contract(case.scenario, case.year)
    if spec.scenario not in (Scenario.C1, Scenario.REALISTA, Scenario.BAU):
        raise NotImplementedError('Cenario 2 requer frota e combustivel integrados')
    if spec.scenario == Scenario.C1 and float(design.get('chp_kw', 0.)) > 0:
        raise NotImplementedError('CHP ainda nao integrado')
    if len(case.load_kw) != len(case.pv_pu) or len(case.load_kw) != len(case.tariff_brl_kwh):
        raise ValueError('Series sinteticas incompatíveis')
    if case.annual_pkm <= 0 or case.annualization_scale <= 0:
        raise ValueError('PKM ou escala invalida')
    pv = float(design.get('pv_kw', 0.))
    bess = float(design.get('bess_kwh', 0.))
    pcs = float(design.get('pcs_kw', 0.))
    if not all(isfinite(x) and x >= 0 for x in (pv,bess,pcs)):
        raise ValueError('Capacidades invalidas')
    if pcs > 0.55*bess + 1e-8:
        return {'status':'INFEASIBLE_DESIGN','reason':'C_RATE', 'design':dict(design)}
    if spec.scenario == Scenario.REALISTA and any(x > 0 for x in (pv,bess,pcs)):
        return {'status':'INFEASIBLE_DESIGN','reason':'REALISTA_NO_LOCAL', 'design':dict(design)}
    if spec.scenario == Scenario.BAU and case.grid_reinforcement_present_brl < 0:
        raise ValueError('Reforco negativo')
    grid_cap = max(case.load_kw) if spec.scenario == Scenario.BAU else None
    m = build_energy_milp(scenario=spec.scenario, year=spec.year,
        load_kw=case.load_kw, pv_pu=case.pv_pu, dt_hours=case.dt_hours,
        pv_kw=pv, bess_kwh=bess, pcs_kw=pcs, grid_cap_kw=grid_cap,
        price_brl_kwh=case.tariff_brl_kwh)
    solved = solve(m)
    if solved['status'] != 'PASS_ENERGY_ONLY':
        return {'status':'INFEASIBLE_MILP','reason':solved.get('termination',solved['status']),
                'design':dict(design)}
    factor = annuity_factor(case.discount_rate, case.years)
    energy_vp = solved['objective_brl']*case.annualization_scale*factor
    capex = pv*case.pv_capex_brl_kw + bess*case.bess_capex_brl_kwh + pcs*case.pcs_capex_brl_kw
    cost = IntegratedCosts(fleet_brl=case.fleet_present_brl,
        infrastructure_brl=capex,
        grid_reinforcement_brl=case.grid_reinforcement_present_brl,
        energy_brl=energy_vp,
        operations_brl=case.annual_operations_brl*factor,
        residual_brl=0., discounted_pkm=case.annual_pkm*factor)
    return {'status':'PASS_SYNTHETIC_ENERGY_ONLY', 'design':dict(design),
        'f1_brl_per_pkm':cost.f1_brl_per_pkm(), 'f2_kw':solved['f2_kw'],
        'costs':vars(cost), 'milp_objective_brl':solved['objective_brl'],
        'classification':'SYNTHETIC_DEMONSTRATION_NOT_D28_SCIENTIFIC_RESULT'}


def optimize_synthetic(case=None, *, population=8, generations=2, seed=42):
    case = case or SyntheticCase()
    if case.scenario != Scenario.C1:
        raise NotImplementedError('Demonstracao evolutiva disponivel somente para C1 sem CHP')
    # PCS e parametrizado por fracao do BESS para respeitar C-rate.
    bounds = {'pv_kw':(0., 1500.), 'bess_kwh':(100., 3000.), 'pcs_fraction':(0., 0.55)}
    evaluations = {}
    def decode(g):
        return {'pv_kw':g['pv_kw'], 'bess_kwh':g['bess_kwh'],
                'pcs_kw':g['bess_kwh']*g['pcs_fraction'], 'chp_kw':0.}
    def objective(g):
        d = decode(g)
        k = tuple(round(d[x], 8) for x in ('pv_kw','bess_kwh','pcs_kw'))
        if k not in evaluations:
            evaluations[k] = evaluate_design(d, case)
        v = evaluations[k]
        return (v['f1_brl_per_pkm'],v['f2_kw']) if v['status']=='PASS_SYNTHETIC_ENERGY_ONLY' else None
    result = run(objective,bounds,population=population,generations=generations,seed=seed)
    nondominated = []
    for i in result['nondominated_indices']:
        d = decode(result['population'][i])
        k = tuple(round(d[x],8) for x in ('pv_kw','bess_kwh','pcs_kw'))
        v = evaluations[k]
        if v['status']=='PASS_SYNTHETIC_ENERGY_ONLY':
            nondominated.append(v)
    return {'status':'PASS_SYNTHETIC_DEMO' if nondominated else 'NO_FEASIBLE_SOLUTION',
        'scenario':case.scenario.value,'year':case.year,
        'evaluations':len(evaluations),'nondominated':nondominated,
        'classification':'SYNTHETIC_DEMONSTRATION_NOT_D28_SCIENTIFIC_RESULT',
        'pending':'Individual charging, CHP, gas fleet, grid expansion economics, evidence gates'}
