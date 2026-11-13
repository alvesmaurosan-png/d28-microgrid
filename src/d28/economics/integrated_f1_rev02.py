"""REV02: auditável, sem parâmetros econômicos inventados.
Contrato: custos em BRL constantes 2026; PKM atendidos anuais; ano t=0..H.
Não resolve MILP: recebe somente despachos certificados e custos sem dupla contagem.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
import math

SCENARIOS = ('BAU', 'Realista', 'Cenario_1', 'Cenario_2')
COST_KEYS = (
    'frota_capex', 'frota_opex', 'frota_reposicao',
    'infra_eletrica_capex', 'infra_eletrica_opex', 'infra_eletrica_reposicao',
    'infra_gas_capex', 'infra_gas_opex', 'infra_gas_reposicao',
    'reforco_rede_capex', 'reforco_rede_opex',
    'energia_eletrica', 'combustivel_diesel', 'arla', 'combustivel_gas',
    'residual_frota', 'residual_infra_eletrica', 'residual_infra_gas',
)
RESIDUAL_KEYS = tuple(k for k in COST_KEYS if k.startswith('residual_'))

class PendingEvidence(ValueError):
    """F1 não computável: há parâmetros/serviço/factibilidade pendentes."""


def _nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name}: exige número finito não negativo')
    return float(value)

@dataclass(frozen=True)
class AnnualRecord:
    year_index: int  # 0 = investimento inicial, 1..H = anos de operação
    pkm_atendidos: float | None
    costs_brl: Mapping[str, float | None]
    service_verified: bool
    dispatch_feasible: bool
    provenance: Mapping[str, str]  # ID Base Mestre, documento, versão e status


def evaluate_integrated_f1(
    scenario: str,
    annual: Sequence[AnnualRecord],
    discount_rate: float,
    horizon_years: int = 20,
    pcc_peak_kw: float | None = None,
    pcc_cap_kw: float | None = None,
    required_cost_keys: Sequence[str] = COST_KEYS,
) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f'Cenário não reconhecido: {scenario}')
    if not isinstance(horizon_years, int) or horizon_years < 1:
        raise ValueError('Horizonte inválido')
    if not math.isfinite(discount_rate) or discount_rate <= -1:
        raise ValueError('Taxa de desconto inválida')
    if len(annual) != horizon_years + 1 or {r.year_index for r in annual} != set(range(horizon_years + 1)):
        raise PendingEvidence('Fluxo incompleto: exige t=0 e todos os anos 1..H')
    if len(set(required_cost_keys)) != len(required_cost_keys) or any(k not in COST_KEYS for k in required_cost_keys):
        raise ValueError('Lista de componentes econômicos inválida')
    if set(required_cost_keys) != set(COST_KEYS):
        raise PendingEvidence('Contrato F1 integrado exige todos os componentes, inclusive zeros comprovados')
    if pcc_peak_kw is None:
        raise PendingEvidence('F2 não certificado pelo MILP')
    f2 = _nonnegative(pcc_peak_kw, 'pcc_peak_kw')
    if pcc_cap_kw is not None and f2 > _nonnegative(pcc_cap_kw, 'pcc_cap_kw') + 1e-6:
        raise PendingEvidence('Despacho viola limite PCC')
    total_vp_cost = 0.0
    total_vp_pkm = 0.0
    vp_by_component = {k: 0.0 for k in COST_KEYS}
    for record in sorted(annual, key=lambda r: r.year_index):
        t = record.year_index
        if not record.dispatch_feasible or not record.service_verified:
            raise PendingEvidence(f't={t}: despacho/serviço não comprovado')
        if record.pkm_atendidos is None:
            raise PendingEvidence(f't={t}: PKM ausente')
        pkm = _nonnegative(record.pkm_atendidos, f't={t} pkm')
        if t == 0 and pkm != 0:
            raise ValueError('PKM em t=0 deve ser zero')
        if t > 0 and pkm <= 0:
            raise PendingEvidence(f't={t}: serviço não atendido')
        missing = [k for k in COST_KEYS if k not in record.costs_brl or record.costs_brl[k] is None]
        if missing:
            raise PendingEvidence(f't={t}: custos pendentes: {missing}')
        unknown = set(record.costs_brl) - set(COST_KEYS)
        if unknown:
            raise ValueError(f't={t}: custos sem categoria econômica: {sorted(unknown)}')
        # Zeros só são aceitos quando explicitamente atestados para cada rubrica.
        for k in COST_KEYS:
            if not record.provenance.get(k, '').strip():
                raise PendingEvidence(f't={t}: ausência de evidência/status para {k}')
        factor = (1.0 + discount_rate) ** t
        total_vp_pkm += pkm / factor
        for k in COST_KEYS:
            amount = _nonnegative(record.costs_brl[k], f't={t} {k}')
            sign = -1 if k in RESIDUAL_KEYS else 1
            vp_by_component[k] += sign * amount / factor
            total_vp_cost += sign * amount / factor
    if total_vp_pkm <= 0:
        raise PendingEvidence('VP(PKM atendidos) não positivo')
    return {
        'status': 'CALCULATED_CONDITIONAL_ON_PROVENANCE',
        'scenario': scenario,
        'f1_integrado_brl_per_pkm': total_vp_cost / total_vp_pkm,
        'f2_peak_pcc_kw': f2,
        'vp_cost_brl': total_vp_cost,
        'vp_pkm_atendidos': total_vp_pkm,
        'vp_cost_by_component_brl': vp_by_component,
        'horizon_years': horizon_years,
        'discount_rate': discount_rate,
        'warning': 'Cálculo não significa homologação de parâmetros; conferir evidências e gates.',
    }
