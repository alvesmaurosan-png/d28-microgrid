"""Contabilidade econômica/ACV R0-R3 condicionada; não altera o despacho.

Todos os valores anuais são entradas documentadas, nunca extrapolados pelo módulo.
R1/R3 usam combustível GN; R2 biogás. CGOB é atributo separado, não
subtrai emissões sem inventário e regra de contabilização explícitos.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping
import math
from d28.economics.f1 import Economics, present_value, annual_bill

ROUTES = ('R0','R1','R2','R3')


def nonnegative(name, value):
    if value is None:
        raise ValueError(f'{name}: evidência/valor ausente')
    v = float(value)
    if not math.isfinite(v) or v < 0:
        raise ValueError(f'{name}: valor inválido')
    return v


@dataclass(frozen=True)
class AnnualAccounting:
    """Valores monetários anuais BRL; emissões de ciclo de vida kgCO2e.

    incremental_present_value_brl: VP dos ativos e custos específicos da rota
    que não estejam incluídos em Economics (CHP, biodigestor, gasômetro etc.).
    annual_fuel_cost_brl: custo do combustível da rota, sem duplicar a conta elétrica.
    lifecycle_kgco2e: inventário ACV TOTAL da arquitetura, não só operação.
    """
    incremental_present_value_brl: float | None = None
    annual_fuel_cost_brl: float | None = None
    lifecycle_kgco2e: float | None = None
    evidence: Mapping[str,str] = field(default_factory=dict)
    cgob_accounting_rule: str | None = None


def annual_objectives(route: str, *, cfg: Economics, pv_kwp: float,
                      bess_kwh: float, pcs_kw: float, grid_kw,
                      months, dt_hours: float, annual_pkm: float,
                      accounting: AnnualAccounting, contract: dict) -> dict:
    """Calcula F1/F2/F3 com entradas anuais explícitas e contrato aprovado.

    Não resolve MILP, não altera objetivo interno e não presume extrapolação.
    A integridade física e temporal da série deve ser verificada a montante.
    """
    from d28.optimization.r0_r3_bridge import annual_contract_ready
    if route not in ROUTES:
        raise ValueError('Arquitetura inválida')
    ready, reason = annual_contract_ready(contract)
    if not ready:
        raise ValueError('ANNUAL_CONTRACT_BLOCKED: ' + reason)
    pkm = nonnegative('annual_pkm', annual_pkm)
    if pkm == 0:
        raise ValueError('annual_pkm deve ser positivo')
    grid = [nonnegative('grid_kw', x) for x in grid_kw]
    if not grid:
        raise ValueError('Série de rede vazia')
    if len(months) != len(grid):
        raise ValueError('Meses e série elétrica incompatíveis')
    keys = set(months)
    if len(keys) != 12 or len({m//100 for m in keys}) != 1:
        raise ValueError('São exigidos 12 meses de um mesmo ano')
    if {m%100 for m in keys} != set(range(1,13)):
        raise ValueError('Meses do ano incompletos')
    # O contrato autoriza a construção anual; a verificação de 8760/8784 h
    # impede que um subconjunto de pontos seja tratado como ano completo.
    year = int(contract['year'])
    leap = (year%4==0 and (year%100!=0 or year%400==0))
    expected_hours = 8784 if leap else 8760
    if not math.isfinite(dt_hours) or dt_hours <= 0 or abs(len(grid)*dt_hours-expected_hours)>1e-6:
        raise ValueError('Horizonte temporal não corresponde ao ano integral')
    if not isinstance(accounting, AnnualAccounting):
        raise ValueError('Contabilidade anual obrigatória')
    if route == 'R3' and not accounting.cgob_accounting_rule:
        raise ValueError('R3: regra de contabilização CGOB ausente')
    if route != 'R0' and not accounting.evidence:
        raise ValueError(f'{route}: evidências específicas ausentes')
    incremental = 0.0 if route == 'R0' and accounting.incremental_present_value_brl is None else nonnegative('incremental_present_value_brl', accounting.incremental_present_value_brl)
    fuel = 0.0 if route == 'R0' and accounting.annual_fuel_cost_brl is None else nonnegative('annual_fuel_cost_brl', accounting.annual_fuel_cost_brl)
    lifecycle = nonnegative('lifecycle_kgco2e', accounting.lifecycle_kgco2e)
    bill = annual_bill(cfg, grid, dt_hours, months)
    pv = present_value(cfg, pv_kwp, bess_kwh, pcs_kw,
                       annual_variable_bill_brl=bill['total_variable_bill_brl']+fuel,
                       annual_pkm=pkm)
    total_pv = pv['pv_total_cost_brl']+incremental
    f1 = total_pv/pv['pv_pkm']
    f2 = max(grid)
    f3 = lifecycle/(pkm*cfg.horizon_years)
    return {'route':route, 'objectives':(f1,f2,f3),
            'units':('BRL/pkm','kW','kgCO2e/pkm'),
            'audit':{'annual_grid_bill_brl':bill['total_variable_bill_brl'],
                     'annual_fuel_cost_brl':fuel,'incremental_present_value_brl':incremental,
                     'total_present_cost_brl':total_pv,'discounted_pkm':pv['pv_pkm'],
                     'lifecycle_kgco2e':lifecycle,'annual_pkm':pkm,
                     'evidence':dict(accounting.evidence),
                     'cgob_accounting_rule':accounting.cgob_accounting_rule,
                     'annual_contract_status':'APPROVED',
                     'internal_dispatch_objective':'not_modified'}}
