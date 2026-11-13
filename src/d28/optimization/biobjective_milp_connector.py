"""D28 REV02: ponte aditiva R0-R3 -> MILP -> despacho -> F1/F2.
Pilotos curtos NÃO produzem F1 nem entram na fronteira científica.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math

from d28.optimization.biobjective_f1_f2 import BiobjectiveResult, annual_f1_f2


@dataclass(frozen=True)
class ConnectorInputs:
    load_kw: tuple[float, ...]
    pv_pu: tuple[float, ...]
    months: tuple[int, ...] = ()  # YYYYMM, apenas para contabilidade anual
    dt_hours: float = 0.25
    pcc_cap_kw: float = 2500.0
    terminal_policy: str = 'cyclic'
    route_options: dict = field(default_factory=dict)


def build_route_milp(route: str, design: dict, inputs: ConnectorInputs):
    from d28.dispatch.milp import build_r0_milp
    from d28.dispatch.r1 import build_r1_milp
    from d28.dispatch.r2_r3 import build_r2_milp, build_r3_milp
    if route not in ('R0', 'R1', 'R2', 'R3'):
        raise ValueError('INVALID_ROUTE')
    if not inputs.load_kw or len(inputs.load_kw) != len(inputs.pv_pu):
        raise ValueError('INVALID_SERIES')
    pv, bess, pcs = (float(design[k]) for k in ('pv_kw', 'bess_kwh', 'pcs_kw'))
    if any(not math.isfinite(x) or x < 0 for x in (pv, bess, pcs)):
        raise ValueError('INVALID_DESIGN')
    if pcs > .55*bess + 1e-9:
        raise ValueError('EQ008_PCS_LIMIT')
    common = dict(pcc_cap_kw=inputs.pcc_cap_kw, dt_hours=inputs.dt_hours,
                  terminal_policy=inputs.terminal_policy)
    args = (list(inputs.load_kw), list(inputs.pv_pu), pv, bess, pcs)
    if route == 'R0':
        return build_r0_milp(*args, **common)
    options = dict(inputs.route_options)
    chp_keys = ('chp_capacity_kw', 'electrical_efficiency',
                'fuel_lhv_kwh_per_nm3', 'availability')
    chp = {key: options[key] for key in chp_keys}  # ausências são bloqueios
    if route == 'R1':
        return build_r1_milp(*args, **common, **chp)
    if route == 'R2':
        keys = ('production_nm3', 'gasometer_capacity_nm3', 'initial_gas_nm3')
        extra = {key: options[key] for key in keys}
        if 'auxiliary_kw' in options:
            extra['auxiliary_kw'] = options['auxiliary_kw']
        if 'terminal_gas_policy' in options:
            extra['terminal_gas_policy'] = options['terminal_gas_policy']
        return build_r2_milp(*args, **common, **chp, **extra)
    if 'cgob_coverage_nm3' not in options:
        raise ValueError('R3_CGOB_COVERAGE_REQUIRED')
    return build_r3_milp(*args, **common, **chp,
                         cgob_coverage_nm3=options['cgob_coverage_nm3'])


def solve_peak_then_energy(model, *, dt_hours=0.25, solver_name='appsi_highs',
                           peak_tolerance_kw=1e-5):
    """Duas MILPs: menor pico e, com pico fixado, menor energia da rede.
    Não é minimização econômica de F1; a política fica registrada.
    """
    import pyomo.environ as p
    if dt_hours <= 0 or peak_tolerance_kw < 0:
        raise ValueError('INVALID_SOLVER_OPTIONS')
    for obj in model.component_data_objects(p.Objective, active=True):
        obj.deactivate()
    model.bio_peak = p.Var(domain=p.NonNegativeReals)
    model.bio_peak_limit = p.Constraint(model.T, rule=lambda m,t: m.grid[t] <= m.bio_peak)
    model.bio_primary = p.Objective(expr=model.bio_peak, sense=p.minimize)
    solver = p.SolverFactory(solver_name)
    if not solver.available(exception_flag=False):
        raise RuntimeError('SOLVER_UNAVAILABLE')
    def solve_once():
        if solver_name == 'appsi_highs':
            solver.config.load_solution = False
        result = solver.solve(model, tee=False)
        term = str(result.solver.termination_condition)
        if result.solver.termination_condition != p.TerminationCondition.optimal:
            return term, False
        if solver_name == 'appsi_highs':
            solver.load_vars()
        else:
            model.solutions.load_from(result)
        return term, True
    first, ok = solve_once()
    if not ok:
        return {'optimal':False, 'grid_kw':(), 'audit':{'primary_termination':first}}
    peak_star = float(p.value(model.bio_peak))
    model.bio_primary.deactivate()
    model.bio_peak_lock = p.Constraint(expr=model.bio_peak <= peak_star + peak_tolerance_kw)
    model.bio_secondary = p.Objective(
        expr=dt_hours*sum(model.grid[t] for t in model.T), sense=p.minimize)
    second, ok = solve_once()
    if not ok:
        return {'optimal':False, 'grid_kw':(), 'audit':{'primary_termination':first,
                                                        'secondary_termination':second}}
    grid = tuple(float(p.value(model.grid[t])) for t in model.T)
    peak = max(grid)
    if peak > peak_star + peak_tolerance_kw + 1e-6:
        raise RuntimeError('PEAK_PRESERVATION_FAILED')
    return {'optimal':True, 'grid_kw':grid,
            'audit':{'primary_termination':first, 'secondary_termination':second,
                     'optimal_peak_kw':peak_star, 'observed_peak_kw':peak,
                     'grid_energy_kwh':sum(grid)*dt_hours,
                     'dispatch_policy':'MIN_PEAK_THEN_MIN_GRID_ENERGY',
                     'dispatch_is_f1_optimal':False}}


def evaluate_route_connected(route, design, inputs: ConnectorInputs, *,
                             economics=None, accounting=None, contract=None,
                             annual_pkm=None, solver_name='appsi_highs'):
    """Piloto: MILP + F2 diagnóstico; anual completo: F1/F2 se contrato válido."""
    try:
        model = build_route_milp(route, design, inputs)
        solved = solve_peak_then_energy(model, dt_hours=inputs.dt_hours,
                                        solver_name=solver_name)
        audit = dict(solved.get('audit') or {})
        audit.update(route=route, intervals=len(inputs.load_kw), dt_hours=inputs.dt_hours,
                     n_obj=2, f3_excluded=True)
        if not solved['optimal']:
            return BiobjectiveResult(route, False, None, 'MILP_NOT_OPTIMAL', audit)
        grid = solved['grid_kw']
        if not grid or min(grid) < -1e-6 or max(grid) > inputs.pcc_cap_kw + 1e-5:
            return BiobjectiveResult(route, False, None, 'GRID_INVALID', audit)
        if len(grid)*inputs.dt_hours not in (8760, 8784):
            audit['pilot_f2_kw'] = max(grid)
            return BiobjectiveResult(route, False, None, 'PILOT_ONLY_NO_ANNUAL_F1', audit)
        if any(x is None for x in (economics, accounting, contract, annual_pkm)):
            return BiobjectiveResult(route, False, None, 'ANNUAL_ACCOUNTING_REQUIRED', audit)
        if len(inputs.months) != len(grid):
            return BiobjectiveResult(route, False, None, 'ANNUAL_MONTHS_REQUIRED', audit)
        obj = annual_f1_f2(route, cfg=economics, pv_kwp=float(design['pv_kw']),
                           bess_kwh=float(design['bess_kwh']), pcs_kw=float(design['pcs_kw']),
                           grid_kw=grid, months=inputs.months, dt_hours=inputs.dt_hours,
                           annual_pkm=annual_pkm, accounting=accounting, contract=contract)
        audit.update(obj['audit'])
        return BiobjectiveResult(route, True, obj['objectives'], 'OPTIMAL_ANNUAL', audit)
    except (ValueError, KeyError, TypeError, RuntimeError, ArithmeticError, ImportError) as exc:
        return BiobjectiveResult(route, False, None, 'CONNECTOR_ERROR',
                                 {'route':route, 'error':f'{type(exc).__name__}: {exc}'})
