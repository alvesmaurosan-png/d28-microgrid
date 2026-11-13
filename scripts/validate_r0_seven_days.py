
import argparse
import inspect
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyomo.environ as p

from d28.dispatch.milp import build_r0_milp

DESIGNS = {
    "A": (205.4806088017267, 28272.75736597176, 4996.651562474392),
    "B": (802.2247646664324, 38208.83648964471, 6640.935872558496),
    "C": (8652.388573894343, 39273.10562110964, 6535.97084299626),
}

def run_design(name, load, solar, pcc, time_limit):
    pv, bess, pcs = DESIGNS[name]
    result = {
        "design": name,
        "pv_kwp": pv,
        "bess_kwh": bess,
        "pcs_kw": pcs,
        "intervals": len(load),
        "status": "NOT_RUN",
    }
    started = time.perf_counter()

    try:
        parameters = {
            "load_kw": load.tolist(),
            "pv_pu": solar.tolist(),
            "pv_capacity_kw": pv,
            "bess_capacity_kwh": bess,
            "pcs_power_kw": pcs,
            "pcc_cap_kw": pcc,
            "dt_hours": 0.25,
            "initial_soc": 0.50,
            "terminal_policy": "cyclic",
        }

        signature = inspect.signature(build_r0_milp)
        required = [
            name for name, par in signature.parameters.items()
            if par.default is inspect.Parameter.empty
            and name not in parameters
        ]
        if required:
            raise TypeError(f"Parametros obrigatorios desconhecidos: {required}")

        model = build_r0_milp(**{
            k: v for k, v in parameters.items()
            if k in signature.parameters
        })

        solver = p.SolverFactory("appsi_highs")
        if not solver.available(exception_flag=False):
            raise RuntimeError("Solver appsi_highs indisponivel")

        solver.config.load_solution = False
        solver.config.time_limit = float(time_limit)

        solved = solver.solve(model, load_solutions=False)
        termination = solved.solver.termination_condition
        result["termination"] = str(termination)

        if termination == p.TerminationCondition.optimal:
            model.solutions.load_from(solved)

            grid = np.array([
                p.value(model.grid[t]) for t in model.T
            ], dtype=float)

            energy = np.array([
                p.value(model.bess_energy[t]) for t in model.S
            ], dtype=float)

            result.update({
                "status": "OPTIMAL",
                "grid_peak_kw": float(grid.max()),
                "grid_energy_kwh": float(grid.sum() * 0.25),
                "soc_initial_kwh": float(energy[0]),
                "soc_terminal_kwh": float(energy[-1]),
                "soc_closure_residual_kwh": float(
                    energy[-1] - energy[0]
                ),
                "bess_energy_min_kwh": float(energy.min()),
                "bess_energy_max_kwh": float(energy.max()),
                "pcc_exceedance_kw": float(
                    max(0.0, grid.max() - pcc)
                ),
            })
        else:
            result["status"] = "NOT_CERTIFIED_OPTIMAL"

    except Exception as exc:
        result["status"] = "ERROR"
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["elapsed_seconds"] = round(
        time.perf_counter() - started, 2
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=float, default=300)
    parser.add_argument("--only", choices=["A", "B", "C"],
                        nargs="+", default=["A", "B", "C"])
    args = parser.parse_args()

    if args.time_limit <= 0:
        parser.error("--time-limit deve ser positivo")

    source = Path(
        "data/processed/milp_inputs/R0_inputs_E100_15min.csv"
    )
    df = pd.read_csv(source)

    columns = [
        "load_charging_ac_kw",
        "pv_kw_per_kwp",
        "dt_hours",
    ]
    if len(df) != 35040 or any(c not in df for c in columns):
        raise ValueError("Entrada anual invalida")

    for col in columns:
        if not np.isfinite(df[col].to_numpy(dtype=float)).all():
            raise ValueError(f"Valores nao finitos: {col}")

    if not np.allclose(df["dt_hours"].to_numpy(), 0.25):
        raise ValueError("Intervalos diferentes de 15 minutos")

    if (df["load_charging_ac_kw"].lt(0).any()
        or df["pv_kw_per_kwp"].lt(0).any()):
        raise ValueError("Demanda ou PV negativos")

    # Dias 356 a 362, indices baseados em zero.
    start = 356 * 96
    stop = 363 * 96

    load = df["load_charging_ac_kw"].to_numpy(
        dtype=float
    )[start:stop]
    solar = df["pv_kw_per_kwp"].to_numpy(
        dtype=float
    )[start:stop]

    assert len(load) == 672

    output = Path("results/r0_seven_days")
    output.mkdir(parents=True, exist_ok=True)
    rows = []

    for name in args.only:
        print(f"RUNNING_{name}: 672 intervals", flush=True)

        result = run_design(
            name, load, solar, 2500.0, args.time_limit
        )
        rows.append(result)

        print(
            "RESULT_" + name,
            json.dumps(result, ensure_ascii=False),
            flush=True,
        )

        pd.DataFrame(rows).to_csv(
            output / "validation_7days.csv",
            index=False,
        )

        (output / "validation_7days.json").write_text(
            json.dumps({
                "scenario": "E100",
                "days_zero_based": [356, 362],
                "terminal_policy": "cyclic",
                "objective": "GRID_ENERGY_NOT_LEX_F2",
                "results": rows,
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print("SEVEN_DAY_VALIDATION_COMPLETE")


if __name__ == "__main__":
    main()
