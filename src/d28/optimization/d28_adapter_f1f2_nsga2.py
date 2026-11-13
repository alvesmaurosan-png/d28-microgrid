"""Adaptador REV16.1: despacho anual reconciliado para F1/F2 NSGA-II."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
import math

@dataclass(frozen=True)
class AdapterResult:
    feasible: bool
    status: str
    objectives: tuple[float,float] | None = None
    audit: dict = field(default_factory=dict)

def evaluate_design(route: str, design: dict, *, contract: dict,
                    evidence_approved: bool, provenance: dict | None,
                    solve_annual_economic: Callable[[str,dict],dict],
                    reconcile_annual: Callable[[str,dict,dict],dict]) -> AdapterResult:
    if route not in ('R0','R1','R2','R3'):
        return AdapterResult(False,'INVALID_ROUTE')
    from d28.optimization.r0_r3_bridge import annual_contract_ready
    ready,reason=annual_contract_ready(contract)
    if not ready:
        return AdapterResult(False,'ANNUAL_CONTRACT_BLOCKED',audit={'reason':reason})
    if not evidence_approved or not provenance:
        return AdapterResult(False,'HOMOLOGATED_EVIDENCE_REQUIRED')
    if not callable(solve_annual_economic) or not callable(reconcile_annual):
        return AdapterResult(False,'CALLBACKS_REQUIRED')
    try:
        solved=solve_annual_economic(route,dict(design))
        if solved.get('status')!='PASS' or not solved.get('checks') or not all(solved['checks'].values()):
            return AdapterResult(False,'MILP_NOT_CERTIFIED',audit={'solver_status':solved.get('status')})
        policy=solved.get('objective')
        valid_policies=('PILOT_VARIABLE_ENERGY_COST_BRL','PILOT_ENERGY_PLUS_MONTHLY_DEMAND_BRL')
        if policy not in valid_policies:
            return AdapterResult(False,'DISPATCH_POLICY_UNVERIFIED',audit={'objective':policy})
        if policy=='PILOT_ENERGY_PLUS_MONTHLY_DEMAND_BRL' and solved.get('demand_charge_in_dispatch_objective') is not True:
            return AdapterResult(False,'DISPATCH_POLICY_UNVERIFIED')
        if policy=='PILOT_VARIABLE_ENERGY_COST_BRL' and solved.get('demand_charge_in_dispatch_objective') is True:
            return AdapterResult(False,'DISPATCH_POLICY_UNVERIFIED')
        if not solved.get('grid_kw') or solved.get('cost_brl') is None or not solved.get('cost_components_brl'):
            return AdapterResult(False,'ANNUAL_DISPATCH_EVIDENCE_MISSING')
        obj=reconcile_annual(route,dict(design),solved)
        values=obj.get('objectives')
        if not isinstance(values,(tuple,list)) or len(values)!=2:
            return AdapterResult(False,'INVALID_OBJECTIVE_SHAPE')
        f1,f2=map(float,values)
        if not all(math.isfinite(v) and v>=0 for v in (f1,f2)):
            return AdapterResult(False,'INVALID_OBJECTIVES')
        if obj.get('units')!=('BRL/pkm','kW') and obj.get('units')!=['BRL/pkm','kW']:
            return AdapterResult(False,'INVALID_OBJECTIVE_UNITS')
        grid=solved['grid_kw']
        if abs(max(map(float,grid))-f2)>1e-5:
            return AdapterResult(False,'F2_GRID_MISMATCH')
        audit=obj.get('audit',{})
        if not isinstance(audit,dict) or not audit.get('demand_reconciled'):
            return AdapterResult(False,'ANNUAL_DEMAND_RECONCILIATION_REQUIRED')
        return AdapterResult(True,'CONDITIONAL_ANNUAL_F1_F2',(f1,f2),
            {'route':route,'dispatch_policy':policy,'epsilon_kw':solved.get('epsilon_kw'),
             'f3_excluded':True,'provenance':provenance,'annual_verified':True,
             'scientific_pareto_certified':False,'economic_audit':audit})
    except (ValueError,TypeError,KeyError,RuntimeError,ArithmeticError) as exc:
        return AdapterResult(False,'ADAPTER_ERROR',audit={'error':f'{type(exc).__name__}: {exc}'})

def as_pymoo_problem(route: str,bounds: dict,evaluator: Callable[[dict],AdapterResult]):
    from d28.optimization.biobjective_f1_f2 import BiobjectiveResult,make_pymoo_problem
    def convert(design):
        r=evaluator(design)
        return BiobjectiveResult(route,r.feasible,r.objectives,r.status,r.audit)
    return make_pymoo_problem(route,bounds,convert)
