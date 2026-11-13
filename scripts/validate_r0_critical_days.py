
import csv
import json
import inspect
import numpy as np
import pandas as pd
from pathlib import Path

from d28.optimization import r0_nsga2_integrated as integrated

ROOT = Path.cwd()
INPUT = ROOT / "data/processed/milp_inputs/R0_inputs_E100_15min.csv"
PARETO = ROOT / "results/r0_nsga2_smoke/pareto_smoke.csv"
OUT = ROOT / "results/r0_critical_days"
OUT.mkdir(parents=True, exist_ok=True)

PCC_KW = 2500.0
DT_H = 0.25
DAY_N = 96

df = pd.read_csv(INPUT)
solutions = pd.read_csv(PARETO)

required = [
    "load_charging_ac_kw",
    "pv_kw_per_kwp",
]
for col in required:
    if col not in df.columns:
        raise RuntimeError(f"Coluna ausente: {col}")

if len(df) != 35040:
    raise RuntimeError(f"Serie anual inesperada: {len(df)} intervalos")

if len(solutions) != 5:
    raise RuntimeError(f"Esperadas cinco solucoes, recebidas {len(solutions)}")

load = df["load_charging_ac_kw"].to_numpy(dtype=float)
solar = df["pv_kw_per_kwp"].to_numpy(dtype=float)

if not np.isfinite(load).all() or not np.isfinite(solar).all():
    raise RuntimeError("Series contem valores nao finitos")

if (load < 0).any() or (solar < 0).any():
    raise RuntimeError("Series contem valores negativos")

load_days = load.reshape(-1, DAY_N)
solar_days = solar.reshape(-1, DAY_N)

daily_peak = load_days.max(axis=1)
daily_energy = load_days.sum(axis=1) * DT_H
daily_solar = solar_days.sum(axis=1) * DT_H

# Deficit potencial: demanda menos geracao PV disponivel,
# antes de qualquer decisao de despacho.
pv_reference = float(solutions["pv_kwp"].median())
daily_deficit = (
    np.maximum(load_days - pv_reference * solar_days, 0)
    .sum(axis=1) * DT_H
)

# Indice combinado apenas para selecionar dia critico.
peak_norm = daily_peak / max(daily_peak.max(), 1)
solar_shortage = 1 - daily_solar / max(daily_solar.max(), 1)
combined = peak_norm + solar_shortage

criteria = {
    "D0_regression": 216,
    "D1_max_peak": int(np.argmax(daily_peak)),
    "D2_max_energy": int(np.argmax(daily_energy)),
    "D3_min_solar": int(np.argmin(daily_solar)),
    "D4_max_pv_deficit": int(np.argmax(daily_deficit)),
    "D5_peak_low_solar": int(np.argmax(combined)),
}

days = {}
for name, day in criteria.items():
    days.setdefault(day, []).append(name)

# Conferencia da interface existente.
signature = inspect.signature(integrated.solve_lex)
print("SOLVE_LEX_SIGNATURE:", signature)

rows = []
for sid, s in solutions.reset_index(drop=True).iterrows():
    pv = float(s["pv_kwp"])
    bess = float(s["bess_kwh"])
    pcs = float(s["pcs_kw"])

    for day, labels in days.items():
        a = day * DAY_N
        b = a + DAY_N

        day_load = load[a:b]
        day_solar = solar[a:b]

        record = {
            "solution": f"S{sid + 1}",
            "day_index": day,
            "criteria": ";".join(labels),
            "pv_kwp": pv,
            "bess_kwh": bess,
            "pcs_kw": pcs,
            "load_peak_kw": float(day_load.max()),
            "load_energy_kwh": float(day_load.sum() * DT_H),
            "solar_kwh_per_kwp": float(day_solar.sum() * DT_H),
            "pcc_cap_kw": PCC_KW,
            "dt_hours": DT_H,
            "status": None,
            "grid_peak_kw": None,
            "grid_energy_kwh": None,
            "balance_residual_kw": None,
        }

        try:
            result = integrated.solve_lex(
                day_load,
                day_solar,
                pv,
                bess,
                pcs
            )

            if result is None:
                record["status"] = "INFEASIBLE_OR_NO_OPTIMUM"
            elif not isinstance(result, dict):
                record["status"] = "UNEXPECTED_RETURN_TYPE"
                record["error"] = type(result).__name__
            else:
                record["status"] = "OPTIMAL"
                record["grid_peak_kw"] = result.get(
                    "F2_kw", result.get("grid_peak_kw")
                )
                record["grid_energy_kwh"] = result.get(
                    "grid_energy_kwh"
                )
                record["balance_residual_kw"] = result.get(
                    "balance_residual_kw"
                )

                if record["grid_peak_kw"] is not None:
                    if float(record["grid_peak_kw"]) > PCC_KW + 1e-5:
                        record["status"] = "PCC_VIOLATION"

        except Exception as exc:
            record["status"] = "SOLVER_ERROR"
            record["error"] = f"{type(exc).__name__}: {exc}"

        rows.append(record)

        print(
            f"{record['solution']} "
            f"day={day:03d} "
            f"status={record['status']} "
            f"peak={record['grid_peak_kw']}"
        )

result_df = pd.DataFrame(rows)

result_path = OUT / "critical_days_validation.csv"
result_df.to_csv(result_path, index=False)

days_df = pd.DataFrame([
    {
        "day_index": day,
        "criteria": ";".join(labels),
        "load_peak_kw": daily_peak[day],
        "load_energy_kwh": daily_energy[day],
        "solar_kwh_per_kwp": daily_solar[day],
    }
    for day, labels in days.items()
])
days_df.to_csv(OUT / "critical_days_selection.csv", index=False)

summary = {
    "scenario": "E100",
    "scope": "critical_days_operational_validation",
    "pcc_cap_kw": PCC_KW,
    "dt_hours": DT_H,
    "solutions": len(solutions),
    "distinct_days": len(days),
    "evaluations": len(rows),
    "status_counts": result_df["status"].value_counts().to_dict(),
    "results": str(result_path),
}

(OUT / "summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\nVALIDATION_SUMMARY")
print(json.dumps(summary, indent=2, ensure_ascii=False))
