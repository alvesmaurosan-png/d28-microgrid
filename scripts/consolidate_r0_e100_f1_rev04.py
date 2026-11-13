from pathlib import Path
import csv
import json
import sys
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from d28.economics.diesel_fleet import (
    DieselAssumptions,
    combine_f1,
)

source = ROOT / "results/r0_e100_consolidacao_rev03/pareto_exato.csv"
diesel_csv = ROOT / "results/diesel_rev02/diesel_summary_rev01.csv"
assumptions_json = ROOT / "results/diesel_rev02/diesel_assumptions_rev01.json"
out_dir = ROOT / "results/r0_e100_f1_consolidada_rev04"
out_dir.mkdir(parents=True, exist_ok=True)

with assumptions_json.open(encoding="utf-8") as f:
    assumptions = DieselAssumptions(**json.load(f))

with diesel_csv.open(encoding="utf-8", newline="") as f:
    diesel = next(
        r for r in csv.DictReader(f)
        if r["scenario"] == "E100"
    )

if not math.isclose(assumptions.real_discount_rate, 0.12):
    raise ValueError("Taxa diesel incompatível com R0")

if diesel["status"] != "EXPLORATORY_CONDITIONAL_NOT_HOMOLOGATED":
    raise ValueError("Status diesel inesperado")

diesel_result = {
    "diesel_fleet_vpl_brl": float(diesel["diesel_fleet_vpl_brl"]),
    "diesel_pkm_pv": float(diesel["diesel_pkm_pv"]),
}

annual_pkm_bev = (
    int(diesel["bev_buses"])
    * assumptions.km_operational_per_bus_month
    * assumptions.months_per_year
    * assumptions.commercial_km_fraction
    * assumptions.mean_passengers_on_board
)

bev_pkm_pv = sum(
    annual_pkm_bev
    * (1 + assumptions.km_growth) ** (t - 1)
    * (1 + assumptions.occupancy_growth) ** (t - 1)
    / (1 + assumptions.real_discount_rate) ** t
    for t in range(1, 21)
)

with source.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    original_fields = list(reader.fieldnames or [])
    candidates = list(reader)

if not candidates:
    raise ValueError("Fronteira REV03 vazia")

extra_fields = [
    "vpl_microgrid_brl",
    "vpl_diesel_fleet_brl",
    "vpl_energy_total_brl",
    "pv_pkm_bev",
    "pv_pkm_diesel",
    "pv_pkm_total",
    "f1_brl_per_pkm",
    "f1_status",
]

results = []

for candidate in candidates:
    if candidate["status"] != "OPTIMAL_MILP":
        raise ValueError("Candidato sem status OPTIMAL_MILP")

    microgrid_vpl = float(candidate["f1_brl"])

    consolidated = combine_f1(
        diesel_result,
        microgrid_vpl_brl=microgrid_vpl,
        bev_pkm_pv=bev_pkm_pv,
    )

    row = dict(candidate)
    row.update(consolidated)
    row["f1_status"] = "EXPLORATORY_CONDITIONAL_NOT_HOMOLOGATED"
    results.append(row)

output = out_dir / "pareto_f1_consolidada.csv"

with output.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=original_fields + extra_fields
    )
    writer.writeheader()
    writer.writerows(results)

print(f"Candidatos processados: {len(results)}")
print(f"PKM BEV descontado: {bev_pkm_pv:,.2f}")
print(f"PKM diesel descontado: {diesel_result['diesel_pkm_pv']:,.2f}")
print(f"F1 mínimo: {min(r['f1_brl_per_pkm'] for r in results):.6f} R$/PKM")
print(f"Arquivo: {output}")
