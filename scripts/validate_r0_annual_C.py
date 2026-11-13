
import argparse
import json
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import pyomo.environ as p

from d28.dispatch.milp import build_r0_milp


DESIGN_A = {
    "pv_capacity_kw": 8652.388573894343,
    "bess_capacity_kwh": 39273.10562110964,
    "pcs_power_kw": 6535.97084299626,
}

PCC_KW = 2500.0
DT_HOURS = 0.25
EXPECTED_INTERVALS = 35040


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=float, default=600.0)
    args = parser.parse_args()

    if args.time_limit <= 0:
        parser.error("--time-limit deve ser positivo")

    output_dir = Path("results/r0_annual_validation")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "annual_C_E100.json"

    result = {
        "experiment": "R0_ANNUAL_C_E100",
        "status": "STARTED",
        "scenario": "E100",
        "intervals": EXPECTED_INTERVALS,
        "dt_hours": DT_HOURS,
        "pcc_kw": PCC_KW,
        "initial_soc": 0.50,
        "terminal_policy": "cyclic",
        "objective": "MIN_GRID_ENERGY_NOT_LEXICOGRAPHIC_F2",
        "time_limit_seconds": args.time_limit,
        **DESIGN_A,
    }

    def save():
        output_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    save()
    started = time.perf_counter()

    try:
        source = Path(
            "data/processed/milp_inputs/R0_inputs_E100_15min.csv"
        )
        df = pd.read_csv(source)

        required = (
            "load_charging_ac_kw",
            "pv_kw_per_kwp",
            "dt_hours",
        )
        if len(df) != EXPECTED_INTERVALS:
            raise ValueError(
                f"Esperados {EXPECTED_INTERVALS} intervalos; "
                f"recebidos {len(df)}"
            )

        if any(column not in df.columns for column in required):
            raise ValueError("Colunas obrigatorias ausentes")

        load = df["load_charging_ac_kw"].to_numpy(dtype=float)
        solar = df["pv_kw_per_kwp"].to_numpy(dtype=float)
        dt = df["dt_hours"].to_numpy(dtype=float)

        if not (
            np.isfinite(load).all()
            and np.isfinite(solar).all()
            and np.isfinite(dt).all()
        ):
            raise ValueError("Entradas contem valores nao finitos")

        if np.any(load < 0) or np.any(solar < 0):
            raise ValueError("Demanda ou PV negativos")

        if not np.allclose(dt, DT_HOURS):
            raise ValueError("Passo temporal diferente de 0,25 h")

        print("ANNUAL_INPUT_OK", flush=True)
        print(
            "BUILDING_ANNUAL_MILP: 35040 intervals",
            flush=True,
        )

        model = build_r0_milp(
            load_kw=load.tolist(),
            pv_pu=solar.tolist(),
            pv_capacity_kw=DESIGN_A["pv_capacity_kw"],
            bess_capacity_kwh=DESIGN_A["bess_capacity_kwh"],
            pcs_power_kw=DESIGN_A["pcs_power_kw"],
            pcc_cap_kw=PCC_KW,
            dt_hours=DT_HOURS,
            initial_soc=0.50,
            terminal_policy="cyclic",
        )

        result["model_build_seconds"] = round(
            time.perf_counter() - started, 3
        )

        solver = p.SolverFactory("appsi_highs")
        if not solver.available(exception_flag=False):
            raise RuntimeError("appsi_highs indisponivel")

        solver.config.load_solution = False
        solver.config.time_limit = args.time_limit

        print(
            "SOLVING_ANNUAL_C: solver_limit_seconds="
            + str(args.time_limit),
            flush=True,
        )

        solve_started = time.perf_counter()
        solved = solver.solve(model, load_solutions=False)

        result["solver_elapsed_seconds"] = round(
            time.perf_counter() - solve_started, 3
        )
        result["termination"] = str(
            solved.solver.termination_condition
        )

        if (
            solved.solver.termination_condition
            == p.TerminationCondition.optimal
        ):
            model.solutions.load_from(solved)

            grid = np.fromiter(
                (p.value(model.grid[t]) for t in model.T),
                dtype=float,
                count=EXPECTED_INTERVALS,
            )
            energy = np.fromiter(
                (p.value(model.bess_energy[t]) for t in model.S),
                dtype=float,
                count=EXPECTED_INTERVALS + 1,
            )

            result.update({
                "status": "OPTIMAL",
                "grid_energy_kwh": float(
                    grid.sum() * DT_HOURS
                ),
                "grid_peak_kw": float(grid.max()),
                "pcc_exceedance_kw": float(
                    max(0.0, grid.max() - PCC_KW)
                ),
                "soc_initial_kwh": float(energy[0]),
                "soc_terminal_kwh": float(energy[-1]),
                "soc_closure_residual_kwh": float(
                    energy[-1] - energy[0]
                ),
                "bess_energy_min_kwh": float(energy.min()),
                "bess_energy_max_kwh": float(energy.max()),
            })
        elif (
            solved.solver.termination_condition
            == p.TerminationCondition.infeasible
        ):
            result["status"] = "INFEASIBLE_REPORTED"
        else:
            result["status"] = "NOT_CERTIFIED_OPTIMAL"

    except Exception as exc:
        result["status"] = "ERROR"
        result["error"] = (
            type(exc).__name__ + ": " + str(exc)
        )
        result["traceback"] = traceback.format_exc()

    finally:
        result["total_elapsed_seconds"] = round(
            time.perf_counter() - started, 3
        )
        save()

        print("ANNUAL_C_RESULT", flush=True)
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            ),
            flush=True,
        )
        print(
            "RESULT_FILE:", output_file,
            flush=True,
        )


if __name__ == "__main__":
    main()
