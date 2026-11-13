"""D28: camada ADITIVA de despacho economico. Nao altera equacoes fisicas.
Custos em BRL; Nm3 de combustivel e gas por INTERVALO.
F1 anual somente via annual_f1_f2 existente e contrato anual validado.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import math
import time
import pyomo.environ as p
from d28.optimization.biobjective_milp_connector import ConnectorInputs, build_route_milp

@dataclass(frozen=True)
class EnergyPrices:
    grid_brl_kwh: tuple[float, ...]
    fuel_brl_nm3: float = 0.
    production_brl_nm3: float = 0.
    gas_loss_brl_nm3: float = 0.
    # Custo incremental de consumo auxiliar somente se nao estiver ja refletido na compra da rede.
    auxiliary_incremental_brl_kwh: float = 0.
    fuel_cost_includes_production: bool = False


def _validate(prices: EnergyPrices, n: int, route: str):
    vals = list(prices.grid_brl_kwh) + [prices.fuel_brl_nm3,prices.production_brl_nm3,
        prices.gas_loss_brl_nm3,prices.auxiliary_incremental_brl_kwh]
    if len(prices.grid_brl_kwh) != n or not all(math.isfinite(float(v)) and float(v)>=0 for v in vals):
        raise ValueError('INVALID_OR_MISSING_ENERGY_PRICES')
    if route == 'R2' and prices.fuel_cost_includes_production and prices.production_brl_nm3 > 0:
        raise ValueError('DOUBLE_COUNT_R2_FUEL_AND_PRODUCTION')


def solve_economic(route: str, design: dict, inputs: ConnectorInputs, prices: EnergyPrices,
                   *, epsilon_kw: float | None = None, solver_name='appsi_highs', tolerance=1e-5,
                   months=None, demand_tariff_brl_kw_month=None, solver_time_limit_seconds=None):
    """Minimiza custo variavel operacional; NAO calcula F1 anual.
    Caso R2: producao e gas_loss sao volumes por intervalo; combustivel R2
    nao e cobrado separadamente se seu custo ja esta na producao (configure 0).
    """
    if solver_time_limit_seconds is not None and (not math.isfinite(float(solver_time_limit_seconds)) or float(solver_time_limit_seconds)<=0):
        raise ValueError('INVALID_SOLVER_TIME_LIMIT')
    n=len(inputs.load_kw)
    _validate(prices,n,route)
    if not math.isfinite(inputs.dt_hours) or inputs.dt_hours<=0: raise ValueError('INVALID_DT')
    if epsilon_kw is not None and (not math.isfinite(epsilon_kw) or epsilon_kw<0): raise ValueError('INVALID_EPSILON')
    m=build_route_milp(route,design,inputs)
    for obj in m.component_data_objects(p.Objective,active=True,descend_into=True): obj.deactivate()
    if epsilon_kw is not None:
        m.rev05_epsilon=p.Constraint(m.T,rule=lambda mm,t: mm.grid[t]<=epsilon_kw)
    ts=list(m.T)
    grid_cost=inputs.dt_hours*sum(prices.grid_brl_kwh[i]*m.grid[t] for i,t in enumerate(ts))
    fuel_cost=prices.fuel_brl_nm3*sum(m.chp.fuel_nm3[t] for t in ts) if route!='R0' else 0.
    production_cost=prices.production_brl_nm3*sum(float(inputs.route_options['production_nm3'][i]) for i in range(n)) if route=='R2' else 0.
    loss_cost=prices.gas_loss_brl_nm3*sum(m.gas_loss[t] for t in ts) if route=='R2' else 0.
    auxiliary_cost=(prices.auxiliary_incremental_brl_kwh*inputs.dt_hours*
        sum(m.auxiliary_load_kw[t] for t in ts)) if route=='R2' else 0.
    # Demand tariff: linear epigraph of monthly maximum grid import.
    # months must align one-to-one with the dispatch intervals (YYYYMM).
    demand_cost = 0.
    demand_enabled = demand_tariff_brl_kw_month is not None
    if demand_enabled:
        tariff = float(demand_tariff_brl_kw_month)
        if not math.isfinite(tariff) or tariff < 0:
            raise ValueError('INVALID_DEMAND_TARIFF')
        if months is None or len(months) != n:
            raise ValueError('DEMAND_MONTHS_REQUIRED')
        month_ids = tuple(dict.fromkeys(months))
        if any(not isinstance(x, int) or x % 100 not in range(1,13) for x in month_ids):
            raise ValueError('INVALID_DEMAND_MONTH')
        if tariff > 0:
            m.rev16_demand_months = p.Set(initialize=month_ids, ordered=True)
            m.rev16_demand_peak = p.Var(m.rev16_demand_months, domain=p.NonNegativeReals)
            m.rev16_demand_epigraph = p.ConstraintList()
            for i,t in enumerate(ts):
                m.rev16_demand_epigraph.add(m.grid[t] <= m.rev16_demand_peak[months[i]])
            demand_cost = tariff * sum(m.rev16_demand_peak[k] for k in month_ids)
    m.rev05_operating_cost=p.Expression(expr=grid_cost+fuel_cost+production_cost+loss_cost+auxiliary_cost+demand_cost)
    m.rev05_economic_objective=p.Objective(expr=m.rev05_operating_cost,sense=p.minimize)
    if solver_name == 'appsi_highs':
        from pyomo.contrib.appsi.solvers import Highs
        solver = Highs()
        if not solver.available():
            raise RuntimeError('SOLVER_UNAVAILABLE')
    else:
        solver = p.SolverFactory(solver_name)
        if not solver.available(exception_flag=False):
            raise RuntimeError('SOLVER_UNAVAILABLE')
    if solver_time_limit_seconds is not None:
        if solver_name == 'appsi_highs':
            solver.config.time_limit = float(solver_time_limit_seconds)
        else:
            # A chave de tempo e especifica de cada solver; nao assumir suporte.
            raise ValueError('TIME_LIMIT_SUPPORTED_ONLY_FOR_APPSI_HIGHS')
    # Never load variables before verifying that HiGHS found a feasible solution.
    # APPsi's persistent interface uses config.load_solution; other solvers use
    # the solve(..., load_solutions=False) keyword.
    solve_start = time.perf_counter()
    try:
        if solver_name == 'appsi_highs':
            solver.config.load_solution = False
            result = solver.solve(m)
        else:
            result = solver.solve(m)
    except RuntimeError as exc:
        return {'route':route,'status':'FAILED',
                'reason':'SOLVER_RUNTIME_ERROR', 'solver_exception':str(exc),
                'solver_termination':'UNKNOWN_AFTER_EXCEPTION', 'solver_state':'ERROR', 'solver_elapsed_seconds':time.perf_counter()-solve_start,
                'milp_executed':True,'f1_annual_brl_per_pkm':None,'f3_excluded':True}
    elapsed = time.perf_counter()-solve_start
    term = result.termination_condition if solver_name == 'appsi_highs' else result.solver.termination_condition
    term_name = str(term).split(".")[-1].strip().lower()
    if term_name != "optimal":
        if term_name in ('infeasible', 'proveninfeasible'):
            state = 'INFEASIBLE'
        elif term_name in ('maxtimelimit', 'timelimit', 'max_time_limit'):
            state = 'TIME_LIMIT'
        else:
            state = 'UNKNOWN'
        return {'route':route,'status':'FAILED','reason':str(term), 'solver_state':state,
                'solver_elapsed_seconds':elapsed, 'solver_termination':str(term),'milp_executed':True,
                'f1_annual_brl_per_pkm':None,'f3_excluded':True}
    if solver_name == 'appsi_highs':
        solver.load_vars()
    else:
        m.solutions.load_from(result)
    grid=[float(p.value(m.grid[t])) for t in ts]
    def value(x): return float(p.value(x))
    components={'grid_brl':value(grid_cost),'fuel_brl':value(fuel_cost),
        'production_brl':value(production_cost),'gas_loss_brl':value(loss_cost),
        'auxiliary_incremental_brl':value(auxiliary_cost)}
    demand_brl=value(demand_cost)
    total=value(m.rev05_operating_cost)
    violation=0.
    for c in m.component_data_objects(p.Constraint,active=True,descend_into=True):
        body=value(c.body)
        if c.has_lb(): violation=max(violation,value(c.lower)-body)
        if c.has_ub(): violation=max(violation,body-value(c.upper))
    peak=max(grid)
    checks={'constraints':violation<=tolerance,
            'epsilon':epsilon_kw is None or peak<=epsilon_kw+tolerance,
            'cost_identity':abs(total-sum(components.values())-demand_brl)<=tolerance,
            'cyclic_bess':abs(value(m.bess_energy[0])-value(m.bess_energy[n]))<=tolerance}
    return {'route':route,'status':'PASS' if all(checks.values()) else 'FAILED',
        'reason':'ECONOMIC_PILOT_ONLY' if all(checks.values()) else 'AUDIT_FAILED',
        'solver_state':'OPTIMAL' if all(checks.values()) else 'AUDIT_FAILED',
        'solver_elapsed_seconds':elapsed, 'solver_termination':str(term),
        'f1_annual_brl_per_pkm':None,'f3_excluded':True,'nsga2_executed':False,
        'annual_accounting_performed':False,'physical_equations_modified':False,
        'objective':'PILOT_ENERGY_PLUS_MONTHLY_DEMAND_BRL' if demand_enabled else 'PILOT_VARIABLE_ENERGY_COST_BRL',
        'demand_charge_in_dispatch_objective':demand_enabled,
        'demand_charge_brl':demand_brl,
        'monthly_peak_kw':({str(k):value(m.rev16_demand_peak[k]) for k in month_ids} if demand_enabled and float(demand_tariff_brl_kw_month)>0 else {}),
        'grid_kw':grid,'pilot_f2_kw':peak,
        'grid_energy_kwh':sum(grid)*inputs.dt_hours,'cost_brl':total,
        'cost_components_brl':components,'max_constraint_violation_native':violation,
        'epsilon_kw':epsilon_kw,'checks':checks}


def annual_f1_f2_strict(route, *, cfg, design, grid_kw, months, dt_hours,
                        annual_pkm, accounting, contract):
    """Reutiliza contabilidade existente; bloqueia qualquer serie nao anual."""
    from d28.optimization.biobjective_f1_f2 import annual_f1_f2
    hours=len(grid_kw)*dt_hours
    if not (abs(hours-8760)<1e-7 or abs(hours-8784)<1e-7):
        raise ValueError('ANNUAL_HORIZON_REQUIRED')
    if len(months)!=len(grid_kw) or len(set(months))!=12:
        raise ValueError('TWELVE_MONTHS_REQUIRED')
    if not math.isfinite(annual_pkm) or annual_pkm<=0:
        raise ValueError('VALIDATED_PASSENGER_KM_REQUIRED')
    if not contract or not accounting or not cfg:
        raise ValueError('VALIDATED_ANNUAL_ECONOMICS_REQUIRED')
    return annual_f1_f2(route,cfg=cfg,pv_kwp=design['pv_kw'],bess_kwh=design['bess_kwh'],
        pcs_kw=design['pcs_kw'],grid_kw=grid_kw,months=months,dt_hours=dt_hours,
        annual_pkm=annual_pkm,accounting=accounting,contract=contract)


def nsga2_objectives_or_infeasible(annual_result):
    """Adaptador para ElementwiseProblem: sem F1 anual, candidato inviavel.
    O driver existente deve mapear F para [F1,F2] e G para [0] ou [1].
    """
    if not annual_result or 'objectives' not in annual_result:
        return {'F':[1e30,1e30],'G':[1.0],'eligible':False}
    objectives=annual_result['objectives']
    if len(objectives)!=2 or not all(math.isfinite(float(x)) for x in objectives):
        return {'F':[1e30,1e30],'G':[1.0],'eligible':False}
    return {'F':[float(objectives[0]),float(objectives[1])],'G':[0.0],'eligible':True}
