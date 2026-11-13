"""REV02.3: camada superior NSGA-II -> resultado MILP -> F1/F2 integrados.

Sem alteração no modelo físico; o provedor MILP é injetado e deve retornar
um CertifiedDispatch pós-solução. Nenhum custo/PKM é inferido da carga.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable, Mapping, Sequence

from d28.economics.integrated_f1_rev02 import AnnualRecord, SCENARIOS
from d28.economics.milp_f1_adapter_rev02 import CertifiedDispatch
from d28.optimization.scenario_evaluator_rev02_2 import ScenarioCandidate, evaluate_candidate


@dataclass(frozen=True)
class ScenarioContract:
    scenario: str
    discount_rate: float
    horizon_years: int
    pcc_cap_kw: float
    economics_source: str


# Provedores externos: MILP já resolvido e fluxo econômico independente.
DispatchProvider = Callable[[str, Mapping[str, float], ScenarioContract], CertifiedDispatch]
EconomicsProvider = Callable[[str, Mapping[str, float], ScenarioContract], Sequence[AnnualRecord]]


def evaluate_design_rev02_3(*, candidate_id: str, design: Mapping[str, float],
                             contract: ScenarioContract, dispatch_provider: DispatchProvider,
                             economics_provider: EconomicsProvider) -> dict:
    """Avalia um projeto. Falhas de provedor são bloqueios, nunca F1/F2 científicos."""
    identity = dict(candidate_id=candidate_id, scenario=contract.scenario, design=dict(design))
    try:
        if contract.scenario not in SCENARIOS:
            raise ValueError('Cenário inválido')
        if not candidate_id.strip():
            raise ValueError('ID ausente')
        if not design or any(not isinstance(k, str) or not k.strip() or
                             isinstance(v, bool) or not isinstance(v, (int, float)) or
                             not isfinite(v) or v < 0 for k, v in design.items()):
            raise ValueError('Dimensionamento inválido')
        # O despacho é produzido por um solver externo. Não é reexecutado aqui.
        dispatch = dispatch_provider(candidate_id, design, contract)
        if not isinstance(dispatch, CertifiedDispatch):
            raise TypeError('Provedor MILP não retornou CertifiedDispatch')
        annual = economics_provider(candidate_id, design, contract)
        candidate = ScenarioCandidate(
            candidate_id=candidate_id, scenario=contract.scenario, design=design,
            dispatch=dispatch, annual_records=annual,
            discount_rate=contract.discount_rate, horizon_years=contract.horizon_years,
            pcc_cap_kw=contract.pcc_cap_kw, economics_source=contract.economics_source,
        )
        return evaluate_candidate(candidate)
    except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
        return {**identity, 'status': 'BLOCKED',
                'f1_integrado_brl_per_pkm': None, 'f2_peak_pcc_kw': None,
                'economics_source': contract.economics_source, 'evidence': None,
                'error': f'{type(exc).__name__}: {exc}'}


def nsga2_evaluation_rev02_3(result: Mapping, *, blocked_objective_placeholder: float = 1e12) -> dict:
    """Converte resultado científico em interface numérica do pymoo.

    G<=0 indica elegibilidade; G>0 bloqueia o indivíduo. O placeholder não é
    resultado científico nem deve ser incluído em fronteiras/relatórios F1/F2.
    """
    if not isfinite(blocked_objective_placeholder) or blocked_objective_placeholder <= 0:
        raise ValueError('Placeholder numérico inválido')
    if result.get('status') != 'EVALUATED_CONDITIONAL':
        return {'F': [blocked_objective_placeholder, blocked_objective_placeholder],
                'G': [1.0], 'scientific_result': dict(result)}
    f1 = result.get('f1_integrado_brl_per_pkm')
    f2 = result.get('f2_peak_pcc_kw')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
           for v in (f1, f2)):
        raise ValueError('Objetivos integrados inválidos em resultado elegível')
    return {'F': [float(f1), float(f2)], 'G': [0.0], 'scientific_result': dict(result)}


def make_pymoo_problem_rev02_3(*, variable_names: Sequence[str], lower_bounds: Sequence[float],
                                 upper_bounds: Sequence[float], contract: ScenarioContract,
                                 dispatch_provider: DispatchProvider,
                                 economics_provider: EconomicsProvider):
    """Cria ElementwiseProblem para NSGA-II; NÃO executa uma otimização."""
    import numpy as np
    names = tuple(variable_names)
    lo, hi = np.asarray(lower_bounds, dtype=float), np.asarray(upper_bounds, dtype=float)
    if (not names or len(set(names)) != len(names) or
        any(not isinstance(n, str) or not n.strip() for n in names) or
        len(lo) != len(names) or len(hi) != len(names) or
        not np.isfinite(lo).all() or not np.isfinite(hi).all() or
        np.any(lo < 0) or np.any(hi <= lo)):
        raise ValueError('Domínio de projeto inválido')

    from pymoo.core.problem import ElementwiseProblem

    class IntegratedProblem(ElementwiseProblem):
        def __init__(self):
            super().__init__(n_var=len(names), n_obj=2, n_ieq_constr=1, xl=lo, xu=hi)
            self.audit_history = []
            self._evaluation_number = 0

        def _evaluate(self, x, out, *args, **kwargs):
            self._evaluation_number += 1
            cid = f'{contract.scenario}_eval_{self._evaluation_number:06d}'
            design = {name: float(value) for name, value in zip(names, x)}
            result = evaluate_design_rev02_3(
                candidate_id=cid, design=design, contract=contract,
                dispatch_provider=dispatch_provider, economics_provider=economics_provider)
            mapped = nsga2_evaluation_rev02_3(result)
            out['F'], out['G'] = mapped['F'], mapped['G']
            self.audit_history.append(mapped['scientific_result'])

    return IntegratedProblem()
