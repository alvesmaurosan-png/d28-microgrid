"""M3.2 — R1 integrado: PV, BESS, rede e CHP a gás natural.

Protótipo físico agregado, ainda não homologado cientificamente.
Não modifica a implementação R0 nem os resultados históricos.
"""

import pyomo.environ as p

from d28.dispatch.milp import build_r0_milp
from d28.dispatch.chp import attach_chp_constraints


def build_r1_milp(
    load_kw,
    pv_pu,
    pv_capacity_kw,
    bess_capacity_kwh,
    pcs_power_kw,
    *,
    chp_capacity_kw,
    electrical_efficiency,
    fuel_lhv_kwh_per_nm3,
    availability,
    minimum_load_fraction=0.50,
    **r0_options,
):
    """Constrói o MILP físico agregado da arquitetura R1.

    O CHP participa do balanço elétrico como geração bruta.
    Não são considerados auxiliares de biodigestão (exclusivos de R2).

    O objetivo herdado de R0 minimiza apenas a energia importada.
    Não representa F1 nem o custo operacional completo de R1.
    """

    model = build_r0_milp(
        load_kw=load_kw,
        pv_pu=pv_pu,
        pv_capacity_kw=pv_capacity_kw,
        bess_capacity_kwh=bess_capacity_kwh,
        pcs_power_kw=pcs_power_kw,
        **r0_options,
    )

    chp = attach_chp_constraints(
        model,
        architecture="R1",
        chp_capacity_kw=chp_capacity_kw,
        electrical_efficiency=electrical_efficiency,
        fuel_lhv_kwh_per_nm3=fuel_lhv_kwh_per_nm3,
        availability=availability,
        minimum_load_fraction=minimum_load_fraction,
    )

    # Substitui o balanço apenas nesta instância do modelo.
    model.del_component(model.balance)

    model.balance = p.Constraint(
        model.T,
        rule=lambda m, t:
            m.grid[t]
            + m.pv[t]
            + m.bess_discharge[t]
            + m.chp.power_gross_kw[t]
            == m.load_kw[t] + m.bess_charge[t],
    )

    model._r0_metadata = dict(model._r0_metadata)
    model._r0_metadata.update({
        "architecture": "R1",
        "scope": "synthetic_aggregate_PV_BESS_NG_CHP",
        "scientific_validation": False,
        "objective_policy": "provisional_grid_energy_only",
        "chp_fuel": "natural_gas",
        "chp_electrical_integration": True,
    })

    return model
