"""Integra os objetivos existentes sem alterar o MILP nem fabricar anualização.

F1/F3 usam exclusivamente annual_objectives, com contrato anual explícito.
F2 pode ser obtido diretamente do despacho em qualquer horizonte.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math
from d28.optimization.annual_accounting_r0_r3 import annual_objectives, AnnualAccounting
from d28.optimization.r0_r3_bridge import annual_contract_ready
from d28.validation.objective_gate import objective_triplet

@dataclass(frozen=True)
class ObjectiveResult:
    route: str
    status: str
    f2_kw: float
    objectives: tuple[float,float,float] | None
    reason: str
    audit: dict


def extract_grid(model):
    """Extrai potência no PCC (kW) de uma solução Pyomo já resolvida."""
    import pyomo.environ as p
    values = tuple(float(p.value(model.grid[t])) for t in model.T)
    if not values or any(not math.isfinite(v) or v < -1e-8 for v in values):
        raise ValueError('PCC ausente ou inválido')
    return tuple(max(0.0,v) for v in values)


def integrate_objectives(route: str, *, grid_kw, contract=None,
                         economics=None, accounting: AnnualAccounting | None=None,
                         pv_kwp=None, bess_kwh=None, pcs_kw=None,
                         months=None, dt_hours=None, annual_pkm=None):
    """Não modifica despacho. Em horizonte diário devolve F2 e bloqueio explícito.

    Em horizonte anual autorizado reutiliza a função anual existente para F1/F2/F3.
    """
    if route not in ('R0','R1','R2','R3'):
        raise ValueError('Arquitetura inválida')
    grid = tuple(float(v) for v in grid_kw)
    if not grid or any(not math.isfinite(v) or v < 0 for v in grid):
        raise ValueError('PCC ausente ou inválido')
    f2 = max(grid)
    ready, reason = annual_contract_ready(contract)
    if not ready:
        return ObjectiveResult(route, 'F2_ONLY_ANNUAL_BLOCKED', f2, None, reason,
                               {'horizon_intervals':len(grid), 'f2_unit':'kW',
                                'f1_f3':'NOT_CALCULATED'})
    if economics is None or accounting is None or months is None or dt_hours is None or annual_pkm is None:
        return ObjectiveResult(route, 'ACCOUNTING_INPUTS_BLOCKED', f2, None,
                               'Entradas econômicas/ACV ou PKM ausentes',
                               {'horizon_intervals':len(grid), 'f1_f3':'NOT_CALCULATED'})
    output = annual_objectives(route, cfg=economics, pv_kwp=pv_kwp,
                               bess_kwh=bess_kwh, pcs_kw=pcs_kw, grid_kw=grid,
                               months=months, dt_hours=dt_hours,
                               annual_pkm=annual_pkm, accounting=accounting,
                               contract=contract)
    objectives = objective_triplet(*output['objectives'])
    if abs(objectives[1]-f2)>1e-8:
        raise ValueError('Inconsistência F2 entre despacho e contabilidade')
    return ObjectiveResult(route, 'THREE_OBJECTIVES_READY', f2, objectives, '',output['audit'])
