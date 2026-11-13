"""REV02.1: ponte estritamente pós-solução entre despacho MILP e F1 integrada.

Não constrói, resolve nem altera o modelo físico. Não inventa custos/PKM.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import math

from d28.economics.integrated_f1_rev02 import (
    AnnualRecord, PendingEvidence, evaluate_integrated_f1,
)


@dataclass(frozen=True)
class CertifiedDispatch:
    """Saída operacional extraída APÓS solver ótimo e variáveis carregadas.

    import_pcc_kw: série efetiva de importação, em kW, sem exportação líquida.
    source: identificação verificável do cenário, run e origem da série.
    """
    termination_condition: str
    import_pcc_kw: Sequence[float]
    expected_intervals: int
    source: str
    timestep_hours: float = 0.25


def adapt_milp_to_integrated_f1(
    *,
    scenario: str,
    dispatch: CertifiedDispatch,
    annual_cost_and_service: Sequence[AnnualRecord],
    discount_rate: float,
    horizon_years: int = 20,
    pcc_cap_kw: float | None = None,
) -> dict:
    """Retorna objetivos somente com despacho certificado e contrato econômico completo.

    Fluxo de custos/PKM é entrada EXTERNA independente; não extrapola um ano
    de despacho para 20 anos e não confunde carga agregada com serviço atendido.
    """
    if dispatch.termination_condition.lower().split('.')[-1] != 'optimal':
        raise PendingEvidence('MILP sem término ótimo certificado')
    if not dispatch.source or not dispatch.source.strip():
        raise PendingEvidence('Origem do despacho não informada')
    if dispatch.expected_intervals <= 0 or len(dispatch.import_pcc_kw) != dispatch.expected_intervals:
        raise PendingEvidence('Série PCC incompleta ou comprimento inconsistente')
    if not math.isfinite(dispatch.timestep_hours) or dispatch.timestep_hours <= 0:
        raise ValueError('Passo temporal inválido')
    if not dispatch.import_pcc_kw:
        raise PendingEvidence('Série PCC vazia')
    values = []
    for i, raw in enumerate(dispatch.import_pcc_kw):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
            raise PendingEvidence(f'Importação PCC inválida no intervalo {i}')
        if raw < -1e-6:
            raise PendingEvidence(f'Importação PCC negativa no intervalo {i}')
        values.append(max(0.0, float(raw)))
    peak = max(values)
    result = evaluate_integrated_f1(
        scenario=scenario,
        annual=annual_cost_and_service,
        discount_rate=discount_rate,
        horizon_years=horizon_years,
        pcc_peak_kw=peak,
        pcc_cap_kw=pcc_cap_kw,
    )
    return {
        **result,
        'dispatch_source': dispatch.source,
        'dispatch_intervals': dispatch.expected_intervals,
        'dispatch_timestep_hours': dispatch.timestep_hours,
        'dispatch_termination': dispatch.termination_condition,
        'f2_source': 'max(import_pcc_kw) pós-MILP',
        'certification_scope': 'condicional; serviço, custos e evidências sujeitos a homologação',
    }
