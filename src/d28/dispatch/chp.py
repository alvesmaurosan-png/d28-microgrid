"""M3.1 — CHP a gás natural: restrições físicas EQ-011 a EQ-013.

Módulo experimental, ainda não homologado cientificamente.
Não altera o modelo R0 nem os resultados históricos.
"""

import math

import pyomo.environ as p


def attach_chp_constraints(
    model,
    *,
    architecture,
    chp_capacity_kw,
    electrical_efficiency,
    fuel_lhv_kwh_per_nm3,
    availability,
    minimum_load_fraction=0.50,
):
    """Acrescenta ao modelo Pyomo as restrições físicas de um CHP.

    Nesta versão, somente R1 (gás natural) é suportada.
    O balanço elétrico existente não é modificado.
    """

    if architecture != "R1":
        raise ValueError("M3.1 suporta exclusivamente a arquitetura R1")

    if not hasattr(model, "T"):
        raise ValueError("Modelo sem conjunto temporal T")

    if not hasattr(model, "_r0_metadata"):
        raise ValueError("Modelo sem metadados temporais R0")

    try:
        capacity = float(chp_capacity_kw)
        efficiency = float(electrical_efficiency)
        lhv = float(fuel_lhv_kwh_per_nm3)
        dt = float(model._r0_metadata["dt_hours"])
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("Parâmetros CHP inválidos ou ausentes") from exc

    if not all(math.isfinite(v) for v in (capacity, efficiency, lhv, dt)):
        raise ValueError("Parâmetros CHP devem ser finitos")

    if capacity <= 0 or not (0 < efficiency <= 1) or lhv <= 0 or dt <= 0:
        raise ValueError("Capacidade, eficiência, PCI e passo temporal inválidos")

    minimum_load_fraction = float(minimum_load_fraction)
    if not math.isfinite(minimum_load_fraction) or not (0 < minimum_load_fraction <= 1):
        raise ValueError("Fração mínima CHP inválida")
    periods = list(model.T)

    try:
        available = list(availability)
    except TypeError as exc:
        raise ValueError("Disponibilidade deve ser uma sequência") from exc

    if len(available) != len(periods):
        raise ValueError("Disponibilidade incompatível com o horizonte temporal")

    if any(type(value) not in (int, bool) or value not in (0, 1)
           for value in available):
        raise ValueError("Disponibilidade deve conter somente 0 ou 1")

    if hasattr(model, "chp"):
        raise ValueError("O modelo já contém um componente CHP")

    block = p.Block()
    model.add_component("chp", block)

    block.T = p.Set(initialize=periods, ordered=True)

    block.available = p.Param(
        block.T,
        initialize=dict(zip(periods, available)),
        within=p.Binary,
    )

    block.on = p.Var(block.T, domain=p.Binary)

    block.power_gross_kw = p.Var(
        block.T,
        domain=p.NonNegativeReals,
    )

    block.fuel_nm3 = p.Var(
        block.T,
        domain=p.NonNegativeReals,
    )

    # EQ-011: carga mínima de 50% quando ligado.
    block.minimum_power = p.Constraint(
        block.T,
        rule=lambda b, t:
        b.power_gross_kw[t] >= minimum_load_fraction * capacity * b.on[t],
    )

    block.maximum_power = p.Constraint(
        block.T,
        rule=lambda b, t:
        b.power_gross_kw[t] <= capacity * b.on[t],
    )

    # EQ-012: indisponibilidade impede o acionamento.
    block.availability_limit = p.Constraint(
        block.T,
        rule=lambda b, t: b.on[t] <= b.available[t],
    )

    # EQ-013: energia elétrica = eficiência × PCI × volume.
    block.fuel_balance = p.Constraint(
        block.T,
        rule=lambda b, t:
        b.power_gross_kw[t] * dt
        == efficiency * lhv * b.fuel_nm3[t],
    )

    return block
