"""REV02.5: conexão pós-solução real do R0, sem alterar o MILP físico.

Atenção: o faturamento aqui exige tarifas e calendário explicitamente fornecidos.
A composição dos demais custos e PKM permanece responsabilidade de um
construtor econômico externo, que deve retornar AnnualRecord completos.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Callable, Mapping, Sequence
from uuid import uuid4

from d28.economics.integrated_f1_rev02 import AnnualRecord, PendingEvidence
from d28.economics.milp_f1_adapter_rev02 import CertifiedDispatch
from d28.optimization.integrated_providers_rev02_4 import (
    EconomicEvidence, IntegratedProvidersRev024, OperationalEvidence,
    make_operational_evidence,
)


def monthly_bill_from_dispatch(*, import_pcc_kw: Sequence[float],
                               months: Sequence[int], dt_hours: float,
                               energy_tariff_brl_kwh: float,
                               demand_tariff_brl_kw_month: float) -> dict:
    """Faturamento simplificado de energia e demanda, sem tributos/bandeiras/ponta.

    Só usar como custo científico quando a tarifa simples corresponder ao
    contrato homologado. Não presume tarifa horossazonal nem 12 meses.
    """
    if not import_pcc_kw or len(import_pcc_kw) != len(months):
        raise ValueError('Série PCC/calendário incompatível')
    for name, value in [('dt_hours', dt_hours),
                        ('energy_tariff_brl_kwh', energy_tariff_brl_kwh),
                        ('demand_tariff_brl_kw_month', demand_tariff_brl_kw_month)]:
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value) or (value <= 0 if name == 'dt_hours' else value < 0):
            raise ValueError(f'{name}: inválido')
    peaks = {}
    total_kwh = 0.0
    for p, m in zip(import_pcc_kw, months):
        if isinstance(p, bool) or not isinstance(p, (float, int)) or not isfinite(p) or p < -1e-7:
            raise ValueError('Potência PCC inválida')
        if not isinstance(m, int) or m < 200001 or m % 100 not in range(1, 13):
            raise ValueError('Mês YYYYMM inválido')
        p = max(0.0, float(p))
        total_kwh += p * dt_hours
        peaks[m] = max(peaks.get(m, 0.0), p)
    energy_cost = total_kwh * energy_tariff_brl_kwh
    demand_cost = sum(peaks.values()) * demand_tariff_brl_kw_month
    return {'grid_energy_kwh': total_kwh, 'monthly_peaks_kw': peaks,
            'energy_cost_brl': energy_cost, 'demand_cost_brl': demand_cost,
            'total_bill_brl': energy_cost + demand_cost,
            'peak_pcc_kw': max(import_pcc_kw)}


@dataclass(frozen=True)
class R0PhysicalInputs:
    load_kw: Sequence[float]
    pv_pu: Sequence[float]
    months: Sequence[int]
    dt_hours: float
    terminal_policy: str = 'cyclic'


@dataclass(frozen=True)
class TariffEvidence:
    energy_tariff_brl_kwh: float
    demand_tariff_brl_kw_month: float
    source: str


# Construtor externo deve usar bill + evidências de CAPEX/OPEX/frota/PKM
# e produzir todos os anos 0..H, sem inferir serviço a partir de kWh.
AnnualEconomicFactory = Callable[[OperationalEvidence, dict, object], Sequence[AnnualRecord]]


def make_r0_integrated_providers(*, physical: R0PhysicalInputs,
                                 tariff: TariffEvidence,
                                 annual_economic_factory: AnnualEconomicFactory,
                                 solver_name: str = 'appsi_highs',
                                 pcc_cap_kw: float | None = None):
    """Executor Pyomo/HiGHS real e builder econômico vinculado ao mesmo despacho.

    Aceita design com pv_kwp, bess_kwh, pcs_kw. Outros componentes da frota
    devem ser tratados pelo construtor econômico externo.
    """
    if solver_name != 'appsi_highs':
        raise ValueError('REV02.5: somente appsi_highs implementado')
    if not tariff.source.strip():
        raise ValueError('Fonte tarifária obrigatória')
    if not physical.load_kw or len(physical.load_kw) != len(physical.pv_pu) or len(physical.load_kw) != len(physical.months):
        raise ValueError('Entradas físicas/calendário incompatíveis')
    if pcc_cap_kw is not None and pcc_cap_kw <= 0:
        raise ValueError('Limite PCC inválido')
    cache = {}

    def executor(candidate_id, design: Mapping[str, float], contract):
        import pyomo.environ as p
        from pyomo.contrib.appsi.solvers import Highs
        from d28.dispatch.milp import build_r0_milp
        for k in ('pv_kwp', 'bess_kwh', 'pcs_kw'):
            if k not in design:
                raise ValueError(f'Dimensionamento ausente: {k}')
        cap = contract.pcc_cap_kw if pcc_cap_kw is None else min(contract.pcc_cap_kw, pcc_cap_kw)
        model = build_r0_milp(
            load_kw=list(physical.load_kw), pv_pu=list(physical.pv_pu),
            pv_capacity_kw=float(design['pv_kwp']),
            bess_capacity_kwh=float(design['bess_kwh']),
            pcs_power_kw=float(design['pcs_kw']),
            pcc_cap_kw=cap, dt_hours=physical.dt_hours,
            terminal_policy=physical.terminal_policy)
        # Objetivo físico original preservado: minimização de importação.
        solver = Highs()
        solver.config.load_solution = False
        result = solver.solve(model)
        termination = str(result.termination_condition)
        if termination.lower().split('.')[-1] != 'optimal':
            raise PendingEvidence(f'MILP_TERMINATION_{termination}')
        solver.load_vars()
        series = [float(p.value(model.grid[t])) for t in model.T]
        run_id = 'rev025_' + uuid4().hex
        dispatch = CertifiedDispatch(
            termination_condition=termination, import_pcc_kw=tuple(series),
            expected_intervals=len(physical.load_kw),
            source=f'pyomo_highs_R0_{run_id}', timestep_hours=physical.dt_hours)
        op = make_operational_evidence(candidate_id=candidate_id,
            scenario=contract.scenario, design=design, run_id=run_id, dispatch=dispatch)
        cache[run_id] = monthly_bill_from_dispatch(
            import_pcc_kw=series, months=physical.months,
            dt_hours=physical.dt_hours,
            energy_tariff_brl_kwh=tariff.energy_tariff_brl_kwh,
            demand_tariff_brl_kw_month=tariff.demand_tariff_brl_kw_month)
        return op

    def builder(operational: OperationalEvidence, contract):
        bill = cache.pop(operational.run_id)
        records = annual_economic_factory(operational, bill, contract)
        # Confirma a consistência entre a fatura e a série certificada.
        check = monthly_bill_from_dispatch(
            import_pcc_kw=operational.dispatch.import_pcc_kw,
            months=physical.months, dt_hours=physical.dt_hours,
            energy_tariff_brl_kwh=tariff.energy_tariff_brl_kwh,
            demand_tariff_brl_kw_month=tariff.demand_tariff_brl_kw_month)
        if check != bill:
            raise PendingEvidence('Faturamento divergente do despacho')
        return EconomicEvidence(
            candidate_id=operational.candidate_id, scenario=operational.scenario,
            run_id=operational.run_id, dispatch_digest=operational.dispatch_digest,
            annual_records=records, source=contract.economics_source,
            energy_costs_from_same_dispatch=True)

    return IntegratedProvidersRev024(executor, builder)
