"""D28: evaluation bridge. No scientific approval is inferred from solver success."""
from dataclasses import dataclass, field
from typing import Callable, Mapping, Any
import math

ROUTES = frozenset(('R0','R1','R2','R3'))

@dataclass(frozen=True)
class CandidateResult:
    route: str
    status: str
    feasible: bool
    f1_brl_pkm: float | None = None
    f2_kw: float | None = None
    f3_kgco2e_pkm: float | None = None
    scientific_eligible: bool = False
    reason: str = ''
    audit: dict = field(default_factory=dict)

    @property
    def objectives(self):
        if not self.scientific_eligible:
            return None
        return (self.f1_brl_pkm, self.f2_kw, self.f3_kgco2e_pkm)


def _finite_nonnegative(value):
    if value is None or isinstance(value, bool):
        return False
    try:
        value = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(value) and value >= 0


def evaluate_candidate(
    route: str,
    design: Mapping[str, Any],
    *,
    build_model: Callable,
    solve_dispatch: Callable,
    compute_f1: Callable | None = None,
    compute_f3: Callable | None = None,
    evidence: Mapping[str, bool] | None = None,
    dt_hours: float = 0.25,
    expected_intervals: int = 35040,
) -> CandidateResult:
    """Callbacks: build_model(route,design), solve_dispatch(model,dt_hours=...).

    Accountants: compute_f1(model, dispatch, route, design), same for F3.
    No implicit tariffs, pkm, emission factors, or approvals.
    """
    audit = {'route': route, 'design': dict(design), 'expected_intervals': expected_intervals}
    if route not in ROUTES:
        return CandidateResult(route,'INVALID_ARCHITECTURE',False,reason='Unknown architecture',audit=audit)
    if not callable(build_model) or not callable(solve_dispatch):
        return CandidateResult(route,'INVALID_CONTRACT',False,reason='Builder or solver missing',audit=audit)
    if not _finite_nonnegative(dt_hours) or dt_hours <= 0 or expected_intervals <= 0:
        return CandidateResult(route,'INVALID_CONTRACT',False,reason='Invalid chronology',audit=audit)
    try:
        model = build_model(route, design)
    except (ValueError, TypeError) as exc:
        return CandidateResult(route,'INVALID_DESIGN',False,reason=str(exc),audit=audit)
    except Exception as exc:
        return CandidateResult(route,'BUILD_ERROR',False,reason=f'{type(exc).__name__}: {exc}',audit=audit)
    try:
        result = solve_dispatch(model, dt_hours=dt_hours)
    except Exception as exc:
        # An exception is not evidence of physical infeasibility.
        return CandidateResult(route,'SOLVER_ERROR',False,reason=f'{type(exc).__name__}: {exc}',audit=audit)
    audit.update(primary_termination=getattr(result,'primary_termination',None),
                 secondary_termination=getattr(result,'secondary_termination',None),
                 peak_preservation_residual_kw=getattr(result,'peak_preservation_residual_kw',None))
    if not getattr(result,'optimal',False):
        reason = str(getattr(result,'reason','NON_OPTIMAL'))
        status = 'INFEASIBLE' if 'infeasible' in (reason+' '+str(audit['primary_termination'])+' '+str(audit['secondary_termination'])).lower() else 'SOLVER_NOT_OPTIMAL'
        return CandidateResult(route,status,False,reason=reason,audit=audit)
    grid = getattr(result,'grid_kw',None)
    if grid is None or len(grid) != expected_intervals or not all(_finite_nonnegative(v) for v in grid):
        return CandidateResult(route,'INVALID_DISPATCH',False,reason='Annual grid series invalid',audit=audit)
    f2 = max(float(v) for v in grid)
    reported_peak = getattr(result,'peak_kw',None)
    if not _finite_nonnegative(reported_peak) or abs(f2-float(reported_peak)) > 1e-4:
        return CandidateResult(route,'INVALID_DISPATCH',False,reason='Peak mismatch',audit=audit)
    audit['intervals'] = len(grid)
    audit['grid_energy_kwh'] = dt_hours*sum(float(v) for v in grid)
    if not callable(compute_f1):
        return CandidateResult(route,'F1_PENDING',True,f2_kw=f2,reason='Economic accountant missing',audit=audit)
    try:
        f1 = compute_f1(model,result,route,design)
    except Exception as exc:
        return CandidateResult(route,'F1_ERROR',True,f2_kw=f2,reason=f'{type(exc).__name__}: {exc}',audit=audit)
    if not _finite_nonnegative(f1):
        return CandidateResult(route,'F1_INVALID',True,f2_kw=f2,reason='Invalid F1',audit=audit)
    if not callable(compute_f3):
        return CandidateResult(route,'F3_PENDING',True,float(f1),f2,reason='LCA accountant missing',audit=audit)
    try:
        f3 = compute_f3(model,result,route,design)
    except Exception as exc:
        return CandidateResult(route,'F3_ERROR',True,float(f1),f2,reason=f'{type(exc).__name__}: {exc}',audit=audit)
    if not _finite_nonnegative(f3):
        return CandidateResult(route,'F3_INVALID',True,float(f1),f2,reason='Invalid F3',audit=audit)
    required = ('annual_inputs_approved','individual_charging_validated','economic_accounting_approved',
                'lifecycle_inventory_complete','lifecycle_factors_approved','model_physics_validated',
                'lexicographic_contract_approved')
    ev = dict(evidence or {})
    missing = [key for key in required if ev.get(key) is not True]
    audit['missing_scientific_evidence'] = missing
    if missing:
        return CandidateResult(route,'THREE_OBJECTIVES_CONDITIONAL',True,float(f1),f2,float(f3),
                               reason='Missing approvals: '+', '.join(missing),audit=audit)
    return CandidateResult(route,'SCIENTIFIC_ELIGIBLE',True,float(f1),f2,float(f3),True,audit=audit)


def nsga2_objectives(results):
    """Fail closed: never silently fill missing F3 or use conditional candidates."""
    results = tuple(results)
    if not results or any(not isinstance(r,CandidateResult) or r.objectives is None for r in results):
        raise ValueError('SCIENTIFIC_PARETO_BLOCKED: incomplete or unapproved evaluation')
    return [list(r.objectives) for r in results]
