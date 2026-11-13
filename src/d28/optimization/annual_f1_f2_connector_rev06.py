"""REV06: ligação anual F1/F2, fail-closed, sem alteração de MILP físico.

Um avaliador por candidato resolve o MILP econômico anual e aplica a
contabilidade anual já existente. Não extrapola pilotos nem aprova contratos.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import json
import math

from d28.optimization.r0_r3_bridge import annual_contract_ready
from d28.optimization.biobjective_f1_f2 import BiobjectiveResult, make_pymoo_problem
from d28.optimization.annual_f1_f2_reconciled_rev09 import annual_f1_f2_reconciled
from d28.optimization.biobjective_milp_connector import ConnectorInputs

ROUTES = ('R0', 'R1', 'R2', 'R3')

@dataclass(frozen=True)
class AnnualEvidence:
    """Entradas auditadas, explicitamente fornecidas para CADA candidato.

    accounting: AnnualAccounting com custos de combustível anuais e VP de ativos.
    Os custos de produção/perdas não podem ser omitidos da contabilidade anual
    quando incorridos; evidência externa é obrigatória para homologação.
    """
    inputs: ConnectorInputs
    prices: object
    economics: object
    accounting: object
    annual_pkm: float
    cost_reconciliation_approved: bool = False
    temporal_evidence_approved: bool = False
    provenance: str = ''


def load_contract(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _check_evidence(route, evidence, contract):
    ready, reason = annual_contract_ready(contract)
    if not ready:
        raise ValueError('ANNUAL_CONTRACT_BLOCKED: ' + reason)
    if route not in ROUTES:
        raise ValueError('INVALID_ROUTE')
    if not isinstance(evidence, AnnualEvidence):
        raise ValueError('ANNUAL_EVIDENCE_REQUIRED')
    if not evidence.temporal_evidence_approved or not evidence.cost_reconciliation_approved:
        raise ValueError('ANNUAL_RECONCILIATION_NOT_APPROVED')
    if not evidence.provenance.strip():
        raise ValueError('ANNUAL_PROVENANCE_REQUIRED')
    x = evidence.inputs
    year = int(contract['year'])
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    n = (8784 if leap else 8760) * 4
    if abs(x.dt_hours - 0.25) > 1e-12 or len(x.load_kw) != n or len(x.pv_pu) != n or len(x.months) != n:
        raise ValueError('FULL_YEAR_15MIN_REQUIRED')
    if set(x.months) != {year * 100 + m for m in range(1,13)}:
        raise ValueError('ANNUAL_MONTHS_INVALID')
    if len(evidence.prices.grid_brl_kwh) != n:
        raise ValueError('ANNUAL_PRICE_SERIES_REQUIRED')
    if not math.isfinite(evidence.annual_pkm) or evidence.annual_pkm <= 0:
        raise ValueError('VALIDATED_PASSENGER_KM_REQUIRED')
    if evidence.economics is None or evidence.accounting is None:
        raise ValueError('ECONOMICS_AND_ACCOUNTING_REQUIRED')


def evaluate_annual(route: str, design: dict, *, contract: dict,
                    evidence_factory: Callable[[str, dict], AnnualEvidence],
                    solver_name='appsi_highs') -> BiobjectiveResult:
    """Avalia candidato com despacho econômico anual; retorna SOMENTE F1/F2.

    Falha de contrato é verificada antes de solicitar dados ou chamar solver.
    O despacho econômico minimiza custos variáveis; F1 anual contabiliza
    CAPEX/OPEX e requer reconciliação explícita de todos os componentes.
    """
    ready, reason = annual_contract_ready(contract)
    if not ready:
        return BiobjectiveResult(route, False, None, 'ANNUAL_CONTRACT_BLOCKED', {'reason':reason})
    if route not in ROUTES:
        return BiobjectiveResult(route, False, None, 'INVALID_ROUTE')
    try:
        evidence = evidence_factory(route, design)
        _check_evidence(route, evidence, contract)
        from d28.optimization.economic_dispatch_f1f2 import solve_economic
        solved = solve_economic(route, design, evidence.inputs, evidence.prices,
                                solver_name=solver_name, months=evidence.inputs.months,
                                demand_tariff_brl_kw_month=evidence.economics.demand_tariff_brl_per_kw_month)
        if solved.get('status') != 'PASS':
            return BiobjectiveResult(route, False, None, 'ANNUAL_MILP_FAILED', {'solver':solved})
        result = annual_f1_f2_reconciled(route, cfg=evidence.economics, design=design,
                grid_kw=solved['grid_kw'], months=evidence.inputs.months,
                dt_hours=evidence.inputs.dt_hours, prices=evidence.prices,
                annual_pkm=evidence.annual_pkm, accounting=evidence.accounting,
                contract=contract, dispatch_components=solved['cost_components_brl'],
                evidence_approved=evidence.cost_reconciliation_approved and evidence.temporal_evidence_approved,
                provenance=evidence.provenance, dispatch_result=solved)
        f1, f2 = result['objectives']
        if abs(f2-solved['pilot_f2_kw']) > 1e-5:
            raise ValueError('F2_DISPATCH_MISMATCH')
        audit = dict(result['audit'])
        audit.update(dispatch_cost_components_brl=solved['cost_components_brl'],
                     dispatch_cost_brl=solved['cost_brl'], provenance=evidence.provenance,
                     dispatch_horizon='ANNUAL', n_obj=2, f3_excluded=True)
        return BiobjectiveResult(route, True, (float(f1),float(f2)), 'OPTIMAL', audit)
    except (ValueError, TypeError, KeyError, RuntimeError, ArithmeticError) as exc:
        return BiobjectiveResult(route, False, None, 'ANNUAL_EVALUATION_BLOCKED',
                                 {'reason':f'{type(exc).__name__}: {exc}'})


def make_annual_problem(route, bounds, *, contract, evidence_factory, solver_name='appsi_highs'):
    """Interface pymoo n_obj=2; não inicia algoritmo automaticamente."""
    ready, reason = annual_contract_ready(contract)
    if not ready:
        raise ValueError('ANNUAL_CONTRACT_BLOCKED: ' + reason)
    return make_pymoo_problem(route, bounds,
        lambda design: evaluate_annual(route, design, contract=contract,
                        evidence_factory=evidence_factory, solver_name=solver_name))
