"""D28: camada biobjetivo sem F3; não altera modelos físicos legados.

A avaliação F1 científica requer contabilidade anual validada. Um piloto
curto só verifica a cadeia técnica e não recebe F1 extrapolada.
"""
from dataclasses import dataclass, field
from typing import Callable, Any
import math

ROUTES = ('R0', 'R1', 'R2', 'R3')

@dataclass(frozen=True)
class BiobjectiveResult:
    route: str
    feasible: bool
    objectives: tuple[float, float] | None
    status: str
    audit: dict = field(default_factory=dict)


def evaluate_biobjective(route: str, design: dict, *, build_model: Callable,
                         solve_dispatch: Callable, compute_f1: Callable | None,
                         annual_verified: bool = False) -> BiobjectiveResult:
    """Callbacks: build_model(route,design); solve_dispatch(model) -> dict.

    solve_dispatch retorna {'optimal':bool,'grid_kw':serie,'audit':dict}.
    compute_f1(model,dispatch,design) retorna F1 em BRL/PKM, NAO custo total.
    Apenas otimalidade comprovada e contrato anual permitem F1/F2.
    """
    if route not in ROUTES:
        return BiobjectiveResult(route, False, None, 'INVALID_ROUTE')
    try:
        model = build_model(route, design)
        dispatch = solve_dispatch(model)
        if not dispatch.get('optimal', False):
            return BiobjectiveResult(route, False, None, 'MILP_NOT_OPTIMAL',
                                     dict(dispatch.get('audit') or {}))
        grid = tuple(float(v) for v in dispatch['grid_kw'])
        if not grid or any(not math.isfinite(v) or v < -1e-6 for v in grid):
            return BiobjectiveResult(route, False, None, 'INVALID_GRID')
        peak = max(0.0, max(grid))
        audit = dict(dispatch.get('audit') or {})
        audit.update(route=route, f2_peak_kw=peak, n_obj=2,
                     f3_excluded=True, annual_verified=bool(annual_verified))
        if not annual_verified:
            return BiobjectiveResult(route, False, None, 'ANNUAL_EVIDENCE_REQUIRED', audit)
        if not callable(compute_f1):
            return BiobjectiveResult(route, False, None, 'F1_ACCOUNTING_REQUIRED', audit)
        f1 = float(compute_f1(model, dispatch, design))
        if not math.isfinite(f1) or f1 < 0:
            return BiobjectiveResult(route, False, None, 'INVALID_F1', audit)
        audit['f1_brl_per_pkm'] = f1
        return BiobjectiveResult(route, True, (f1, peak), 'OPTIMAL', audit)
    except (ValueError, TypeError, KeyError, RuntimeError, ArithmeticError) as exc:
        return BiobjectiveResult(route, False, None, 'EVALUATION_ERROR',
                                 {'error': f'{type(exc).__name__}: {exc}'})


def annual_f1_f2(route: str, *, cfg, pv_kwp, bess_kwh, pcs_kw,
                 grid_kw, months, dt_hours, annual_pkm, accounting, contract):
    """Adapta contabilidade legada sem solicitar lifecycle_kgco2e.

    Mantém os gates temporais e econômicos originais; não muda o despacho.
    """
    from d28.optimization.r0_r3_bridge import annual_contract_ready
    from d28.optimization.annual_accounting_r0_r3 import nonnegative, ROUTES
    from d28.economics.f1 import present_value, annual_bill
    if route not in ROUTES:
        raise ValueError('Arquitetura inválida')
    ready, reason = annual_contract_ready(contract)
    if not ready:
        raise ValueError('ANNUAL_CONTRACT_BLOCKED: ' + reason)
    pkm = nonnegative('annual_pkm', annual_pkm)
    if pkm <= 0:
        raise ValueError('annual_pkm deve ser positivo')
    grid = [nonnegative('grid_kw', x) for x in grid_kw]
    if not grid or len(months) != len(grid):
        raise ValueError('Séries temporais incompatíveis')
    keys = set(months)
    if len(keys) != 12 or len({m//100 for m in keys}) != 1 or {m%100 for m in keys} != set(range(1,13)):
        raise ValueError('Exigidos 12 meses completos de um ano')
    year = int(contract['year'])
    leap = year%4 == 0 and (year%100 != 0 or year%400 == 0)
    hours = 8784 if leap else 8760
    if not math.isfinite(dt_hours) or dt_hours <= 0 or abs(len(grid)*dt_hours-hours)>1e-6:
        raise ValueError('Horizonte anual inválido')
    from d28.optimization.annual_accounting_r0_r3 import AnnualAccounting
    if not isinstance(accounting, AnnualAccounting):
        raise ValueError('Contabilidade anual obrigatória')
    if route != 'R0' and not accounting.evidence:
        raise ValueError('Evidências específicas da rota ausentes')
    if route == 'R3' and not accounting.cgob_accounting_rule:
        raise ValueError('Regra CGOB ausente')
    incremental = (0.0 if route == 'R0' and accounting.incremental_present_value_brl is None
                   else nonnegative('incremental_present_value_brl', accounting.incremental_present_value_brl))
    fuel = (0.0 if route == 'R0' and accounting.annual_fuel_cost_brl is None
            else nonnegative('annual_fuel_cost_brl', accounting.annual_fuel_cost_brl))
    bill = annual_bill(cfg, grid, dt_hours, months)
    pv = present_value(cfg, pv_kwp, bess_kwh, pcs_kw,
                       annual_variable_bill_brl=bill['total_variable_bill_brl'] + fuel,
                       annual_pkm=pkm)
    denom = float(pv['pv_pkm'])
    if denom <= 0 or not math.isfinite(denom):
        raise ValueError('PKM descontado inválido')
    f1 = (pv['pv_total_cost_brl'] + incremental) / denom
    f2 = max(grid)
    if not all(math.isfinite(v) and v >= 0 for v in (f1, f2)):
        raise ValueError('Objetivos inválidos')
    return {'route':route, 'objectives':(f1,f2), 'units':('BRL/pkm','kW'),
            'audit':{'annual_grid_bill_brl':bill['total_variable_bill_brl'],
                     'annual_fuel_cost_brl':fuel,
                     'incremental_present_value_brl':incremental,
                     'total_present_cost_brl':pv['pv_total_cost_brl']+incremental,
                     'discounted_pkm':denom,'annual_pkm':pkm,
                     'evidence':dict(accounting.evidence),
                     'cgob_accounting_rule':accounting.cgob_accounting_rule,
                     'annual_contract_status':'APPROVED',
                     'f3_excluded':True}}


def make_pymoo_problem(route: str, bounds, evaluator: Callable):
    """evaluator(design)->BiobjectiveResult; inviáveis via restrição G>0."""
    import numpy as np
    from pymoo.core.problem import ElementwiseProblem
    names = tuple(bounds)
    lower = np.array([bounds[n][0] for n in names], dtype=float)
    upper = np.array([bounds[n][1] for n in names], dtype=float)
    if not len(names) or np.any(lower > upper) or not np.isfinite(lower).all() or not np.isfinite(upper).all():
        raise ValueError('Limites inválidos')
    class Problem(ElementwiseProblem):
        def __init__(self):
            super().__init__(n_var=len(names), n_obj=2, n_ieq_constr=1, xl=lower, xu=upper)
            self.records = []
        def _evaluate(self, x, out, *args, **kwargs):
            design = dict(zip(names, map(float, x)))
            result = evaluator(design)
            if result.feasible and result.objectives is not None:
                out['F'] = list(result.objectives)
                out['G'] = [-1.0]
            else:
                out['F'] = [1e15, 1e9]
                out['G'] = [1.0]
            self.records.append({'route':route, 'design':design,
                                 'status':result.status,'feasible':result.feasible,
                                 'objectives':result.objectives,'audit':result.audit})
    return Problem()
