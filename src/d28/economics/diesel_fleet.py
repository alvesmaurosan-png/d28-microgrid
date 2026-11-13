"""D28 diesel fleet economic module REV01; conditional exploratory inputs.

All prices are in constant BRL 2026; CHP gas/biogas costs are NOT included here.
Annual transport and cost are scenario-fixed; never add these to MILP dispatch.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import json
import math

SCENARIOS = {"E100": (2026, 100), "E200": (2026, 200), "E300": (2026, 300),
             "E375": (2038, 375), "E450": (2050, 450)}

@dataclass(frozen=True)
class DieselAssumptions:
    fleet_total: int = 450
    km_operational_per_bus_month: float = 5574.0  # external proxy, not measured D28
    months_per_year: int = 12
    commercial_km_fraction: float = 0.90  # hypothetical
    mean_passengers_on_board: float = 23.0  # hypothetical
    diesel_brl_per_liter: float = 7.22  # illustrative, not validated contract price
    arla_liters_per_diesel_liter: float = 0.04  # hypothetical; verify SCR applicability
    arla_brl_per_liter: float = 3.0  # hypothetical
    real_discount_rate: float = 0.08  # hypothetical; replace with approved protocol rate
    km_growth: float = 0.0
    occupancy_growth: float = 0.0
    diesel_real_price_growth: float = 0.0
    infrastructure_capex_brl: float = 0.0  # PENDING, zero is not verified absence
    infrastructure_opex_brl_year: float = 0.0  # PENDING
    infrastructure_replacement_brl_year10: float = 0.0  # PENDING
    infrastructure_residual_brl_year20: float = 0.0  # PENDING


def read_categories(path: str | Path) -> list[tuple[str, float, float]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    categories = [(r["category"], float(r["share"]), float(r["liters_per_km_ac"])) for r in rows]
    if not categories or not math.isclose(sum(r[1] for r in categories), 1, abs_tol=1e-9):
        raise ValueError("Category shares must sum to 1")
    if any(share < 0 or lpkm <= 0 for _, share, lpkm in categories):
        raise ValueError("Invalid category inputs")
    return categories


def allocate_diesel_buses(n: int, categories: list[tuple[str, float, float]]) -> list[int]:
    """Same spreadsheet rule: round first n-1 classes; last gets remainder.

    Python round is ties-to-even; spreadsheet ROUND rounds halves away from zero.
    """
    alloc = [int(math.floor(n * share + 0.5)) for _, share, _ in categories[:-1]]
    alloc.append(n - sum(alloc))
    if min(alloc) < 0:
        raise ValueError("Negative category allocation")
    return alloc


def calculate_scenario(scenario: str, categories: list[tuple[str, float, float]],
                       p: DieselAssumptions = DieselAssumptions()) -> dict:
    if scenario not in SCENARIOS:
        raise KeyError(scenario)
    year_base, bev = SCENARIOS[scenario]
    diesel = p.fleet_total - bev
    if diesel < 0 or not (0 <= p.commercial_km_fraction <= 1) or p.real_discount_rate <= -1:
        raise ValueError("Invalid assumptions")
    allocations = allocate_diesel_buses(diesel, categories)
    liters_per_fleet_km = sum(n * lpkm for n, (_, _, lpkm) in zip(allocations, categories))
    rows = []
    for t in range(1, 21):
        km_factor = (1 + p.km_growth) ** (t - 1)
        occupancy = p.mean_passengers_on_board * (1 + p.occupancy_growth) ** (t - 1)
        km_per_bus = p.km_operational_per_bus_month * p.months_per_year * km_factor
        operational_km = diesel * km_per_bus
        commercial_km = operational_km * p.commercial_km_fraction
        liters = liters_per_fleet_km * km_per_bus
        price_factor = (1 + p.diesel_real_price_growth) ** (t - 1)
        diesel_cost = liters * p.diesel_brl_per_liter * price_factor
        arla_cost = liters * p.arla_liters_per_diesel_liter * p.arla_brl_per_liter * price_factor
        infra_opex = p.infrastructure_opex_brl_year if diesel else 0.0
        annual_cost = diesel_cost + arla_cost + infra_opex
        pkm = commercial_km * occupancy
        discount = (1 + p.real_discount_rate) ** t
        rows.append(dict(scenario=scenario, year=t, calendar_year=year_base + t - 1,
                         diesel_buses=diesel, operational_km=operational_km,
                         commercial_km=commercial_km, diesel_liters=liters,
                         diesel_cost_brl=diesel_cost, arla_cost_brl=arla_cost,
                         infra_opex_brl=infra_opex, annual_cost_brl=annual_cost,
                         pv_cost_brl=annual_cost / discount, pkm_diesel=pkm,
                         pv_pkm_diesel=pkm / discount))
    capex = p.infrastructure_capex_brl if diesel else 0.0
    replacement = (p.infrastructure_replacement_brl_year10 / (1 + p.real_discount_rate) ** 10) if diesel else 0.0
    residual = (p.infrastructure_residual_brl_year20 / (1 + p.real_discount_rate) ** 20) if diesel else 0.0
    return dict(scenario=scenario, base_year=year_base, bev_buses=bev, diesel_buses=diesel,
                categories=[dict(name=name, buses=n, liters_per_km=lpkm)
                            for n, (name, _, lpkm) in zip(allocations, categories)],
                annual=rows,
                diesel_fleet_vpl_brl=sum(r["pv_cost_brl"] for r in rows) + capex + replacement - residual,
                diesel_pkm_pv=sum(r["pv_pkm_diesel"] for r in rows),
                status="EXPLORATORY_CONDITIONAL_NOT_HOMOLOGATED")


def combine_f1(diesel_result: dict, microgrid_vpl_brl: float,
               bev_pkm_pv: float) -> dict:
    """microgrid_vpl includes all PV/BESS/grid/CHP costs ONCE, no bus diesel fuel.

    Both PKM denominators must use same discount rate and 20-year horizon.
    """
    if not all(math.isfinite(x) for x in (microgrid_vpl_brl, bev_pkm_pv)) or bev_pkm_pv < 0:
        raise ValueError("Invalid BEV values")
    total_pkm = diesel_result["diesel_pkm_pv"] + bev_pkm_pv
    if total_pkm <= 0:
        raise ValueError("Total PV PKM must be positive")
    total_cost = diesel_result["diesel_fleet_vpl_brl"] + microgrid_vpl_brl
    return dict(f1_brl_per_pkm=total_cost / total_pkm,
                vpl_energy_total_brl=total_cost,
                vpl_microgrid_brl=microgrid_vpl_brl,
                vpl_diesel_fleet_brl=diesel_result["diesel_fleet_vpl_brl"],
                pv_pkm_total=total_pkm,
                pv_pkm_bev=bev_pkm_pv,
                pv_pkm_diesel=diesel_result["diesel_pkm_pv"])


def export_scenarios(categories_csv: str | Path, output_dir: str | Path,
                     assumptions: DieselAssumptions = DieselAssumptions()) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    categories = read_categories(categories_csv)
    results = [calculate_scenario(s, categories, assumptions) for s in SCENARIOS]
    with (out / "diesel_annual_rev01.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(results[0]["annual"][0])
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerows(result["annual"])
    with (out / "diesel_summary_rev01.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "base_year", "bev_buses", "diesel_buses",
                                             "diesel_fleet_vpl_brl", "diesel_pkm_pv", "status"])
        writer.writeheader()
        for result in results:
            writer.writerow({k: result[k] for k in writer.fieldnames})
    with (out / "diesel_assumptions_rev01.json").open("w", encoding="utf-8") as f:
        json.dump(assumptions.__dict__, f, indent=2, ensure_ascii=False)
