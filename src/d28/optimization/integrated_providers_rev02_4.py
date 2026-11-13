"""REV02.4: provedores com uma única execução MILP e trilha física-econômica.

O executor real é injetado; este módulo não altera o MILP, não cria custos,
não extrapola serviço e não confunde resultado histórico com F1 integrada.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from typing import Callable, Mapping, Sequence

from d28.economics.integrated_f1_rev02 import AnnualRecord
from d28.economics.milp_f1_adapter_rev02 import CertifiedDispatch
from d28.optimization.nsga2_scenario_bridge_rev02_3 import (
    ScenarioContract, evaluate_design_rev02_3, nsga2_evaluation_rev02_3,
)


def _digest(candidate_id: str, scenario: str, design: Mapping[str, float], series: Sequence[float]) -> str:
    payload = {'candidate_id': candidate_id, 'scenario': scenario,
               'design': sorted((k, float(v)) for k, v in design.items()),
               'import_pcc_kw': [float(v) for v in series]}
    return sha256(json.dumps(payload, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class OperationalEvidence:
    candidate_id: str
    scenario: str
    design: Mapping[str, float]
    dispatch: CertifiedDispatch
    # Origem dos custos de energia, identificada pela mesma impressão digital do despacho.
    run_id: str
    dispatch_digest: str


@dataclass(frozen=True)
class EconomicEvidence:
    candidate_id: str
    scenario: str
    run_id: str
    dispatch_digest: str
    annual_records: Sequence[AnnualRecord]
    source: str
    # Declaração de vínculo dos custos de energia com o despacho: verificável pelo provedor.
    energy_costs_from_same_dispatch: bool


# Implementações reais deverão encapsular solve(model), leitura de model.grid e
# faturamento, sem alterar equações ou usar dados de outro run.
OperationalExecutor = Callable[[str, Mapping[str, float], ScenarioContract], OperationalEvidence]
EconomicBuilder = Callable[[OperationalEvidence, ScenarioContract], EconomicEvidence]


class IntegratedProvidersRev024:
    """Estado de avaliação isolado por candidato; sem cache inter-candidatos."""

    def __init__(self, executor: OperationalExecutor, builder: EconomicBuilder):
        self.executor = executor
        self.builder = builder
        self._active: dict[str, tuple[OperationalEvidence, EconomicEvidence]] = {}
        self.audit: list[dict] = []

    def _check_operational(self, evidence: OperationalEvidence, cid: str,
                           design: Mapping[str, float], contract: ScenarioContract) -> None:
        if not isinstance(evidence, OperationalEvidence):
            raise TypeError('Executor deve retornar OperationalEvidence')
        if evidence.candidate_id != cid or evidence.scenario != contract.scenario:
            raise ValueError('Identidade do despacho divergente')
        if dict(evidence.design) != dict(design):
            raise ValueError('Dimensionamento do despacho divergente')
        if not evidence.run_id.strip():
            raise ValueError('Identificador do run MILP ausente')
        d = evidence.dispatch
        if not isinstance(d, CertifiedDispatch):
            raise TypeError('Despacho não certificado')
        if d.termination_condition.lower().split('.')[-1] != 'optimal':
            raise ValueError('MILP sem término ótimo')
        if d.expected_intervals <= 0 or len(d.import_pcc_kw) != d.expected_intervals:
            raise ValueError('Série PCC incompleta')
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
               not isfinite(x) or x < -1e-6 for x in d.import_pcc_kw):
            raise ValueError('Série PCC inválida')
        if evidence.dispatch_digest != _digest(cid, contract.scenario, design, d.import_pcc_kw):
            raise ValueError('Impressão digital do despacho divergente')
        if evidence.run_id not in d.source:
            raise ValueError('Fonte do despacho não contém identificador do run')

    def _check_economic(self, economic: EconomicEvidence, operational: OperationalEvidence,
                        contract: ScenarioContract) -> None:
        if not isinstance(economic, EconomicEvidence):
            raise TypeError('Construtor econômico deve retornar EconomicEvidence')
        if (economic.candidate_id != operational.candidate_id or
            economic.scenario != operational.scenario or
            economic.run_id != operational.run_id or
            economic.dispatch_digest != operational.dispatch_digest):
            raise ValueError('Custos e despacho não pertencem à mesma avaliação')
        if not economic.energy_costs_from_same_dispatch:
            raise ValueError('Custo de energia não vinculado ao despacho certificado')
        if not economic.source.strip() or economic.source != contract.economics_source:
            raise ValueError('Fonte econômica divergente ou ausente')
        if not economic.annual_records:
            raise ValueError('Fluxos econômicos ausentes')

    def evaluate(self, *, candidate_id: str, design: Mapping[str, float],
                 contract: ScenarioContract) -> dict:
        """Resolve MILP exatamente uma vez, constrói custos desse run e avalia REV02.3."""
        self._active.clear()
        def dispatch_provider(cid, x, c):
            operational = self.executor(cid, x, c)
            self._check_operational(operational, cid, x, c)
            economic = self.builder(operational, c)
            self._check_economic(economic, operational, c)
            self._active[cid] = (operational, economic)
            return operational.dispatch

        def economics_provider(cid, x, c):
            if cid not in self._active:
                raise RuntimeError('Despacho não executado para este candidato')
            return self._active[cid][1].annual_records

        try:
            result = evaluate_design_rev02_3(
                candidate_id=candidate_id, design=design, contract=contract,
                dispatch_provider=dispatch_provider, economics_provider=economics_provider)
            if candidate_id in self._active:
                op, econ = self._active[candidate_id]
                result = {**result, 'run_id': op.run_id,
                          'dispatch_digest': op.dispatch_digest,
                          'economic_evidence_source': econ.source}
            self.audit.append(result)
            return result
        finally:
            self._active.clear()

    def evaluate_for_nsga2(self, *, candidate_id: str, design: Mapping[str, float],
                           contract: ScenarioContract) -> dict:
        return nsga2_evaluation_rev02_3(
            self.evaluate(candidate_id=candidate_id, design=design, contract=contract))


def make_operational_evidence(*, candidate_id: str, scenario: str,
                              design: Mapping[str, float], run_id: str,
                              dispatch: CertifiedDispatch) -> OperationalEvidence:
    """Auxiliar de empacotamento pós-solver; não certifica sozinho a origem da série."""
    return OperationalEvidence(candidate_id, scenario, dict(design), dispatch, run_id,
                               _digest(candidate_id, scenario, design, dispatch.import_pcc_kw))
