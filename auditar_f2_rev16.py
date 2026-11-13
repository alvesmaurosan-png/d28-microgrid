import json
from pathlib import Path

import rodar_d28_rev16_1 as base

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "D28_AUDITORIA_F2_REV16.json"

x, series_path, start = base.inputs()
cfg = base.Economics.from_json(
    ROOT / "config/economics/r0_f1_exploratory_2026.json"
)

design = {
    "pv_kw": 1908.225,
    "bess_kwh": 15000.0,
    "pcs_kw": 5500.0
}

prices = base.EnergyPrices(
    grid_brl_kwh=(
        float(cfg.energy_tariff_brl_per_kwh),
    ) * len(x.load_kw)
)

results = []

for epsilon in [2500.0, 2450.0, 2400.0, 2300.0]:
    print(
        f"TESTANDO EPSILON = {epsilon:.1f} kW",
        flush=True
    )

    r = base.solve_economic(
        "R0",
        design,
        x,
        prices,
        epsilon_kw=epsilon,
        solver_name="appsi_highs"
    )

    row = {
        "epsilon_kw": epsilon,
        "status": r.get("status"),
        "reason": r.get("reason"),
        "pilot_f2_kw": r.get("pilot_f2_kw"),
        "grid_energy_kwh": r.get("grid_energy_kwh"),
        "operating_cost_brl": r.get("cost_brl"),
        "checks": r.get("checks")
    }

    if r.get("status") == "PASS":
        grid = r["grid_kw"]
        actual_peak = max(grid)

        if abs(actual_peak - r["pilot_f2_kw"]) > 1e-6:
            raise RuntimeError(
                "F2 divergente do maximo da serie"
            )

        if actual_peak > epsilon + 1e-5:
            raise RuntimeError(
                "Violacao do limite epsilon"
            )

        bill = base.temporal_bill(
            grid,
            prices.grid_brl_kwh,
            x.months,
            x.dt_hours,
            cfg.demand_tariff_brl_per_kw_month
        )

        cap = base.present_value(
            cfg,
            design["pv_kw"],
            design["bess_kwh"],
            design["pcs_kw"],
            annual_variable_bill_brl=bill["total_brl"],
            annual_pkm=137675700
        )

        row["f1_brl_per_pkm"] = (
            cap["pv_total_cost_brl"] / cap["pv_pkm"]
        )
        row["annual_energy_total_brl"] = bill["total_brl"]
        row["present_energy_cost_brl"] = cap["pv_total_cost_brl"]

    results.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8"
)
print("RELATORIO:", OUT)
