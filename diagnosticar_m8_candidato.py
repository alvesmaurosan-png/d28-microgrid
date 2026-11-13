
import json
from pathlib import Path

import numpy as np
import pandas as pd

from d28.optimization.r0_nsga2_milp import R0Problem, Economics


INPUT = Path("data/processed/milp_inputs/R0_inputs_E100_15min.csv")
ECONOMICS = Path("config/economics/r0_f1_exploratory_2026.json")
OUTPUT = Path("results/M8_DIAGNOSTICO_CANDIDATO_02")

# Candidato rejeitado na execução anual original
PV_KWP = 244.46963671229352
BESS_KWH = 9007.718757911343
PCS_KW = 4860.09185342315
PEAK_LIMIT_KW = 2316.9124721215044

PCS_MAX_KW = 5500.0


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT, nrows=35040)

    if len(df) != 35040:
        raise ValueError("Calendário anual incompleto")

    load = df["load_charging_ac_kw"].to_numpy(dtype=float)
    solar = df["pv_kw_per_kwp"].to_numpy(dtype=float)
    months = pd.to_datetime(
        df["interval_start_local"]
    ).dt.month.tolist()

    cfg = Economics.from_json(str(ECONOMICS))

    problem = R0Problem(
        load,
        solar,
        months,
        cfg,
        0.25,
        bounds=[
            (0.0, 1908.225),
            (0.0, 20000.0),
            (0.0, PCS_MAX_KW),
        ],
        peak_range=(0.0, float(cfg.pcc_import_limit_kw)),
        solver_name="appsi_highs",
    )

    # Reconstrução das variáveis normalizadas do NSGA-II
    peak_max = float(cfg.pcc_import_limit_kw)
    alpha = PEAK_LIMIT_KW / peak_max

    pcs_required = max(
        float(np.max(load - PV_KWP * solar - PEAK_LIMIT_KW)),
        0.0,
    )

    pcs_upper = min(PCS_MAX_KW, 0.55 * BESS_KWH)

    if pcs_upper < pcs_required:
        raise RuntimeError(
            "Candidato viola EQ008 antes da solução MILP"
        )

    fraction = (
        (PCS_KW - pcs_required) / (pcs_upper - pcs_required)
        if pcs_upper > pcs_required
        else 0.0
    )

    x = np.array(
        [PV_KWP, BESS_KWH, fraction, alpha],
        dtype=float,
    )

    out = {}
    problem._evaluate(x, out)

    report = {
        "candidate": {
            "pv_kwp": PV_KWP,
            "bess_kwh": BESS_KWH,
            "pcs_kw": PCS_KW,
            "peak_limit_kw": PEAK_LIMIT_KW,
        },
        "pcs_required_kw": pcs_required,
        "pcs_upper_kw": pcs_upper,
        "normalized_variables": x.tolist(),
        "history": problem.history,
        "optimizer_objectives": np.asarray(
            out.get("F", []), dtype=float
        ).tolist(),
    }

    (OUTPUT / "diagnostico.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
