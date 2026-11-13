"""REV02.2: avaliação pós-MILP e comparação de cenários, sem modificar despacho.

O otimizador pode chamar evaluate_candidate após resolver o MILP. Dados anuais
são fornecidos por fonte externa: não são inferidos do despacho de um ano.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from typing import Mapping, Sequence

from d28.economics.integrated_f1_rev02 import AnnualRecord, PendingEvidence, SCENARIOS
from d28.economics.milp_f1_adapter_rev02 import (
    CertifiedDispatch, adapt_milp_to_integrated_f1,
)


@dataclass(frozen=True)
class ScenarioCandidate:
    candidate_id: str
    scenario: str
    design: Mapping[str, float]
    dispatch: CertifiedDispatch
    annual_records: Sequence[AnnualRecord]
    discount_rate: float
    horizon_years: int
    pcc_cap_kw: float | None = None
    economics_source: str = ""


def evaluate_candidate(candidate: ScenarioCandidate) -> dict:
    """Retorna objetivos científicos apenas quando todos os gates passam.

    Em caso de falha, não atribui penalidades numéricas a F1/F2: o NSGA-II
    deverá tratar a restrição de maneira explícita, em camada própria.
    """
    identity = {
        "candidate_id": candidate.candidate_id,
        "scenario": candidate.scenario,
        "design": dict(candidate.design),
    }
    try:
        if not candidate.candidate_id.strip():
            raise PendingEvidence("ID do candidato ausente")
        if candidate.scenario not in SCENARIOS:
            raise PendingEvidence("Cenário não reconhecido")
        if not candidate.economics_source.strip():
            raise PendingEvidence("Origem econômica não informada")
        if not candidate.design:
            raise PendingEvidence("Dimensionamento não informado")
        for key, value in candidate.design.items():
            if (not isinstance(key, str) or not key.strip() or
                    isinstance(value, bool) or not isinstance(value, (int, float)) or
                    not isfinite(value) or value < 0):
                raise PendingEvidence("Dimensionamento contém valores inválidos")
        objectives = adapt_milp_to_integrated_f1(
            scenario=candidate.scenario,
            dispatch=candidate.dispatch,
            annual_cost_and_service=candidate.annual_records,
            discount_rate=candidate.discount_rate,
            horizon_years=candidate.horizon_years,
            pcc_cap_kw=candidate.pcc_cap_kw,
        )
        return {
            **identity,
            "status": "EVALUATED_CONDITIONAL",
            "f1_integrado_brl_per_pkm": objectives["f1_integrado_brl_per_pkm"],
            "f2_peak_pcc_kw": objectives["f2_peak_pcc_kw"],
            "economics_source": candidate.economics_source,
            "evidence": objectives,
            "error": None,
        }
    except (PendingEvidence, ValueError, TypeError, OverflowError) as exc:
        return {
            **identity,
            "status": "BLOCKED",
            "f1_integrado_brl_per_pkm": None,
            "f2_peak_pcc_kw": None,
            "economics_source": candidate.economics_source,
            "evidence": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def evaluate_scenario_comparison(
    candidates: Sequence[ScenarioCandidate],
    *,
    require_all_scenarios: bool = True,
    service_relative_tolerance: float = 1e-9,
    service_absolute_tolerance: float = 1e-6,
) -> dict:
    """Compara cenários somente quando o vetor anual de PKM é equivalente.

    Não classifica a fronteira de Pareto nem executa otimização.
    Um candidato por cenário neste comparador: múltiplos candidatos requerem
    uma etapa de seleção explícita, sem escolhas automáticas silenciosas.
    """
    results = [evaluate_candidate(c) for c in candidates]
    errors: list[str] = []
    if not candidates:
        errors.append("Nenhum candidato informado")
    names = [c.scenario for c in candidates]
    if len(names) != len(set(names)):
        errors.append("Há múltiplos candidatos do mesmo cenário; seleção pendente")
    if require_all_scenarios and set(names) != set(SCENARIOS):
        errors.append("Conjunto de cenários incompleto ou desconhecido")
    if any(r["status"] != "EVALUATED_CONDITIONAL" for r in results):
        errors.append("Há candidatos bloqueados")
    if candidates:
        ref = candidates[0]
        ref_service = {r.year_index: r.pkm_atendidos for r in ref.annual_records}
        for c in candidates[1:]:
            if c.horizon_years != ref.horizon_years:
                errors.append(f"{c.scenario}: horizonte distinto")
            if not isclose(c.discount_rate, ref.discount_rate, rel_tol=0, abs_tol=1e-12):
                errors.append(f"{c.scenario}: taxa de desconto distinta")
            other = {r.year_index: r.pkm_atendidos for r in c.annual_records}
            if ref_service.keys() != other.keys():
                errors.append(f"{c.scenario}: anos de serviço distintos")
                continue
            for year in ref_service:
                a, b = ref_service[year], other[year]
                if (a is None or b is None or not isfinite(a) or not isfinite(b)
                        or not isclose(a, b, rel_tol=service_relative_tolerance,
                                       abs_tol=service_absolute_tolerance)):
                    errors.append(f"{c.scenario}: PKM não equivalente no ano {year}")
                    break
    return {
        "status": "COMPARABLE_CONDITIONAL" if not errors else "BLOCKED",
        "results": results,
        "errors": errors,
        "comparison_basis": "PKM atendidos anuais iguais; horizonte e taxa de desconto comuns",
        "homologated": False,
    }
