import sys
import json
import hashlib
from pathlib import Path

import pandas as pd
import pyomo.environ as p

sys.path.insert(0, "src")

from d28.dispatch.r1 import build_r1_milp
from d28.optimization.annual_lexicographic_dispatch import solve_annual_lexicographic

root = Path.cwd()
source = root / "data/processed/milp_inputs/R0_inputs_E100_15min.csv"
reference = root / "results/r0_annual_validation/annual_A_E100.json"
out = root / "results/r1_annual_validation/E100"

df = pd.read_csv(source)
r0 = json.loads(reference.read_text(encoding="utf-8"))

input_hash = hashlib.sha256(source.read_bytes()).hexdigest()

assert len(df) == 35040
assert (df["dt_hours"] == 0.25).all()
assert input_hash == "2f01a4ed51ae92688296f802095988dd0eb739f6cd938821da5da4d82e5f6d44"

out.mkdir(parents=True, exist_ok=True)

print("ENTRADAS_ANUAIS_VALIDADAS", flush=True)

model = build_r1_milp(
    load_kw=df["load_charging_ac_kw"].tolist(),
    pv_pu=df["pv_kw_per_kwp"].tolist(),
    pv_capacity_kw=r0["pv_capacity_kw"],
    bess_capacity_kwh=r0["bess_capacity_kwh"],
    pcs_power_kw=r0["pcs_power_kw"],
    chp_capacity_kw=1000.0,
    electrical_efficiency=0.35,
    fuel_lhv_kwh_per_nm3=9.5,
    availability=[1] * len(df),
    minimum_load_fraction=0.5,
    pcc_cap_kw=r0["pcc_kw"],
    dt_hours=0.25,
)

print("MODELO_R1_CONSTRUIDO", flush=True)
print("INICIANDO_HIGHS_LEXICOGRAFICO", flush=True)

result = solve_annual_lexicographic(
    model,
    dt_hours=0.25,
    peak_tolerance_kw=1e-5,
    solver_name="appsi_highs",
)

summary = {
    "architecture": "R1",
    "scenario": "E100",
    "classification": "CONTRAFACTUAL_EXPLORATORIO",
    "scientific_homologation": False,
    "intervals": len(df),
    "dt_hours": 0.25,
    "pv_capacity_kw": r0["pv_capacity_kw"],
    "bess_capacity_kwh": r0["bess_capacity_kwh"],
    "pcs_power_kw": r0["pcs_power_kw"],
    "pcc_cap_kw": r0["pcc_kw"],
    "chp_capacity_kw": 1000.0,
    "electrical_efficiency": 0.35,
    "fuel_lhv_kwh_per_nm3": 9.5,
    "minimum_load_fraction": 0.5,
    "availability_assumption": "100_percent_idealized",
    "input_sha256": input_hash,
    "r0_reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
    "optimal": result.optimal,
    "reason": result.reason,
    "primary_termination": str(result.primary_termination),
    "secondary_termination": str(result.secondary_termination),
    "peak_preservation_residual_kw": result.peak_preservation_residual_kw,
    "peak_kw": result.peak_kw,
    "grid_energy_kwh": result.grid_energy_kwh,
}

if result.optimal:
    times = list(model.T)

    dispatch = pd.DataFrame({
        "interval_index": df["interval_index"].to_numpy(),
        "interval_start_local": df["interval_start_local"].to_numpy(),
        "load_kw": df["load_charging_ac_kw"].to_numpy(),
        "grid_kw": [p.value(model.grid[t]) for t in times],
        "pv_kw": [p.value(model.pv[t]) for t in times],
        "bess_charge_kw": [p.value(model.bess_charge[t]) for t in times],
        "bess_discharge_kw": [p.value(model.bess_discharge[t]) for t in times],
        "chp_kw": [p.value(model.chp.power_gross_kw[t]) for t in times],
    })

    dispatch["balance_residual_kw"] = (
        dispatch["grid_kw"]
        + dispatch["pv_kw"]
        + dispatch["bess_discharge_kw"]
        + dispatch["chp_kw"]
        - dispatch["load_kw"]
        - dispatch["bess_charge_kw"]
    )

    dispatch.to_csv(out / "r1_e100_dispatch.csv", index=False)

    summary["max_balance_residual_kw"] = float(
        dispatch["balance_residual_kw"].abs().max()
    )

    print("R1_E100_OPTIMAL", flush=True)
    print("PICO_PCC_KW:", summary["peak_kw"])
    print("ENERGIA_REDE_KWH:", summary["grid_energy_kwh"])
    print("RESIDUO_MAX_BALANCO_KW:", summary["max_balance_residual_kw"])
else:
    print("R1_E100_NAO_OTIMO:", result.reason, flush=True)

(out / "r1_e100_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("RESULTADOS:", out, flush=True)
