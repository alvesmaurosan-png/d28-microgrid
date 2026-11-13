"""D28 REV05.1 - Integracao cientifica incremental.

Nao altera o MILP, o NSGA-II ou as APIs publicas existentes.
F1/F2 economicos sao calculados independentemente de F3.
A elegibilidade cientifica e avaliada em etapa separada.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math

from d28.economics.f1 import (
    Economics,
    annual_bill,
    present_value,
)
from d28.optimization.annual_accounting_r0_r3 import (
    AnnualAccounting,
    annual_objectives,
)
from d28.optimization.r0_r3_bridge import annual_contract_ready
from d28.optimization.scientific_contract import (
    ScientificEvidence,
    assess,
)

ROUTES = ("R0", "R1", "R2", "R3")


@dataclass(frozen=True)
class ScientificObjectiveResult:
    route: str
    status: str
    f1_brl_per_pkm: float | None
    f2_kw: float | None
    f3_kgco2e_per_pkm: float | None
    audit: dict
    reason: str = ""


def integrate_scientific_objectives(
    route: str,
    *,
    grid_kw,
    contract,
    economics: Economics,
    accounting: AnnualAccounting,
    pv_kwp: float,
    bess_kwh: float,
    pcs_kw: float,
    months,
    dt_hours: float,
    annual_pkm: float,
):
    """Contabilidade condicionada, sem presumir homologacao."""
    if route not in ROUTES:
        raise ValueError("Arquitetura invalida")

    ready, reason = annual_contract_ready(contract)
    if not ready:
        return ScientificObjectiveResult(
            route, "ANNUAL_CONTRACT_BLOCKED",
            None, None, None, {}, reason
        )

    if not isinstance(accounting, AnnualAccounting):
        raise ValueError("AnnualAccounting obrigatorio")

    if not isinstance(economics, Economics):
        raise ValueError("Economics obrigatorio")

    year = int(contract["year"])
    leap = (
        year % 4 == 0
        and (year % 100 != 0 or year % 400 == 0)
    )
    expected_hours = 8784 if leap else 8760

    grid = tuple(float(x) for x in grid_kw)
    months = tuple(months)

    if (
        not grid
        or not math.isfinite(dt_hours)
        or dt_hours <= 0
        or abs(len(grid) * dt_hours - expected_hours) > 1e-6
    ):
        raise ValueError("Horizonte anual incompleto")

    if abs(dt_hours - 0.25) > 1e-9:
        raise ValueError("Resolucao cientifica exige 15 minutos")

    if len(grid) != len(months):
        raise ValueError("Calendario e despacho incompatíveis")

    expected_months = {year * 100 + m for m in range(1, 13)}
    if set(months) != expected_months:
        raise ValueError("Calendario mensal incompleto")

    if any(
        not isinstance(x, int) or x not in expected_months
        for x in months
    ):
        raise ValueError("Identificador mensal invalido")

    # Verifica que os intervalos seguem a ordem do calendario.
    from d28.economics.f1 import month_groups

    expected_sequence = tuple(
        month_groups(
            datetime(year, 1, 1),
            len(grid),
            dt_hours,
        )
    )
    if months != expected_sequence:
        raise ValueError("Cronologia mensal inconsistente")

    if not math.isfinite(annual_pkm) or annual_pkm <= 0:
        raise ValueError("PKM anual invalido")

    if route == "R3" and not accounting.cgob_accounting_rule:
        raise ValueError("Regra CGOB ausente")

    if route != "R0" and not accounting.evidence:
        raise ValueError("Evidencias da arquitetura ausentes")

    incremental = accounting.incremental_present_value_brl
    fuel = accounting.annual_fuel_cost_brl

    if route == "R0":
        incremental = 0.0 if incremental is None else incremental
        fuel = 0.0 if fuel is None else fuel

    for name, value in (
        ("incremental_present_value_brl", incremental),
        ("annual_fuel_cost_brl", fuel),
    ):
        if (
            value is None
            or not math.isfinite(float(value))
            or float(value) < 0
        ):
            raise ValueError(name + ": valor ausente ou invalido")

    bill = annual_bill(economics, grid, dt_hours, months)

    pv = present_value(
        economics,
        pv_kwp,
        bess_kwh,
        pcs_kw,
        annual_variable_bill_brl=(
            bill["total_variable_bill_brl"] + float(fuel)
        ),
        annual_pkm=annual_pkm,
    )

    f1 = (
        pv["pv_total_cost_brl"] + float(incremental)
    ) / pv["pv_pkm"]
    f2 = max(grid)

    audit = {
        "annual_grid_bill_brl": bill["total_variable_bill_brl"],
        "annual_fuel_cost_brl": float(fuel),
        "incremental_present_value_brl": float(incremental),
        "total_present_cost_brl": (
            pv["pv_total_cost_brl"] + float(incremental)
        ),
        "discounted_pkm": pv["pv_pkm"],
        "annual_pkm": annual_pkm,
        "intervals": len(grid),
        "year": year,
        "accounting_evidence": dict(accounting.evidence),
        "annual_contract_status": "APPROVED",
        "physical_validation": "NOT_ASSERTED",
        "individual_charging": "NOT_ASSERTED",
        "economic_homologation": "NOT_ASSERTED",
        "internal_dispatch_objective": "not_modified",
    }

    lifecycle = accounting.lifecycle_kgco2e

    if lifecycle is None:
        return ScientificObjectiveResult(
            route,
            "F1_F2_COMPUTED_F3_PENDING",
            f1, f2, None, audit,
            "Inventario ambiental incompleto",
        )

    # Reutiliza integralmente a implementacao legada
    # quando todos os objetivos estiverem disponiveis.
    output = annual_objectives(
        route,
        cfg=economics,
        pv_kwp=pv_kwp,
        bess_kwh=bess_kwh,
        pcs_kw=pcs_kw,
        grid_kw=grid,
        months=months,
        dt_hours=dt_hours,
        annual_pkm=annual_pkm,
        accounting=accounting,
        contract=contract,
    )

    f1_old, f2_old, f3 = output["objectives"]

    if (
        abs(f1_old - f1) > 1e-7 * max(1.0, abs(f1))
        or abs(f2_old - f2) > 1e-7
    ):
        raise ValueError("Divergencia com contabilidade legada")

    return ScientificObjectiveResult(
        route,
        "F1_F2_F3_COMPUTED_NOT_HOMOLOGATED",
        f1, f2, f3, audit,
    )


def assess_scientific_result(
    result: ScientificObjectiveResult,
    *,
    scenario: str,
    dispatch_optimal: bool,
    physics_validated: bool,
    individual_charging_validated: bool,
    source_manifest_sha256: str | None,
    f1_homologated: bool = False,
    f2_homologated: bool = False,
    f3_homologated: bool = False,
    lca_complete: bool = False,
):
    """Aplica gates sem homologar resultados automaticamente."""
    intervals = int(result.audit.get("intervals", 0))
    evidence = ScientificEvidence(
        architecture=result.route,
        scenario=scenario,
        temporal_intervals=intervals,
        interval_hours=0.25,
        dispatch_optimal=dispatch_optimal,
        physics_validated=physics_validated,
        individual_charging_validated=individual_charging_validated,
        f1_brl_per_pkm=result.f1_brl_per_pkm,
        f2_kw=result.f2_kw,
        f3_kgco2e_per_pkm=result.f3_kgco2e_per_pkm,
        f1_homologated=f1_homologated,
        f2_homologated=f2_homologated,
        f3_homologated=f3_homologated,
        lca_complete=lca_complete,
        source_manifest_sha256=source_manifest_sha256,
    )
    return assess(evidence)
