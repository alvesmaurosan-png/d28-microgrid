
import argparse
import json
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import pyomo.environ as p

from d28.dispatch.milp import build_r0_milp

PV_KWP = 802.2247646664324
BESS_KWH = 38208.83648964471
PCS_KW = 6640.935872558496
PCC_KW = 2500.0
DT_H = 0.25
N = 35040


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--epsilon-kw", type=float, default=0.001)
    args = parser.parse_args()

    if args.time_limit <= 0 or args.epsilon_kw < 0:
        parser.error("Tempo positivo e epsilon nao negativo")

    outdir = Path("results/r0_annual_lexicographic")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "annual_B_lexicographic_E100.json"

    result = {
        "experiment": "R0_ANNUAL_B_LEXICOGRAPHIC_E100",
        "status": "STARTED",
        "scenario": "E100",
        "intervals": N,
        "dt_hours": DT_H,
        "pv_kwp": PV_KWP,
        "bess_kwh": BESS_KWH,
        "pcs_kw": PCS_KW,
        "pcc_kw": PCC_KW,
        "initial_soc": 0.5,
        "terminal_policy": "cyclic",
        "epsilon_kw": args.epsilon_kw,
        "time_limit_per_stage_seconds": args.time_limit,
        "stage_1": {},
        "stage_2": {},
    }

    def save():
        outfile.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    started = time.perf_counter()
    save()

    try:
        df = pd.read_csv(
            "data/processed/milp_inputs/R0_inputs_E100_15min.csv"
        )
        required = (
            "load_charging_ac_kw",
            "pv_kw_per_kwp",
            "dt_hours",
        )
        if len(df) != N or any(c not in df for c in required):
            raise ValueError("Arquivo anual invalido")

        load = df["load_charging_ac_kw"].to_numpy(dtype=float)
        solar = df["pv_kw_per_kwp"].to_numpy(dtype=float)
        dt = df["dt_hours"].to_numpy(dtype=float)

        if not (
            np.isfinite(load).all()
            and np.isfinite(solar).all()
            and np.isfinite(dt).all()
        ):
            raise ValueError("Dados nao finitos")
        if np.any(load < 0) or np.any(solar < 0):
            raise ValueError("Demanda ou PV negativos")
        if not np.allclose(dt, DT_H):
            raise ValueError("Passo temporal diferente de 0,25 h")

        print("ANNUAL_INPUT_OK", flush=True)
        print("BUILDING_LEXICOGRAPHIC_MILP", flush=True)

        m = build_r0_milp(
            load_kw=load.tolist(),
            pv_pu=solar.tolist(),
            pv_capacity_kw=PV_KWP,
            bess_capacity_kwh=BESS_KWH,
            pcs_power_kw=PCS_KW,
            pcc_cap_kw=PCC_KW,
            dt_hours=DT_H,
            initial_soc=0.50,
            terminal_policy="cyclic",
        )

        result["build_seconds"] = round(
            time.perf_counter() - started, 3
        )

        solver = p.SolverFactory("appsi_highs")
        if not solver.available(exception_flag=False):
            raise RuntimeError("appsi_highs indisponivel")

        solver.config.load_solution = False
        solver.config.time_limit = args.time_limit

        # P1: minimizar pico anual de importacao.
        m.obj.deactivate()
        m.annual_peak = p.Var(
            domain=p.NonNegativeReals,
            bounds=(0.0, PCC_KW),
        )
        m.annual_peak_limit = p.Constraint(
            m.T,
            rule=lambda model, t:
                model.grid[t] <= model.annual_peak,
        )
        m.lex_peak_objective = p.Objective(
            expr=m.annual_peak,
            sense=p.minimize,
        )

        print("STAGE_1_MIN_ANNUAL_PEAK", flush=True)
        t1 = time.perf_counter()
        solved1 = solver.solve(m, load_solutions=False)

        result["stage_1"] = {
            "termination": str(
                solved1.solver.termination_condition
            ),
            "elapsed_seconds": round(
                time.perf_counter() - t1, 3
            ),
        }
        save()

        if (
            solved1.solver.termination_condition
            != p.TerminationCondition.optimal
        ):
            result["status"] = "STAGE_1_NOT_OPTIMAL"
            print("STAGE_1_NOT_OPTIMAL", flush=True)
            return

        m.solutions.load_from(solved1)

        f2_star = float(p.value(m.annual_peak))
        grid1 = np.fromiter(
            (p.value(m.grid[t]) for t in m.T),
            dtype=float,
            count=N,
        )

        result["stage_1"].update({
            "F2_star_kw": f2_star,
            "grid_peak_kw": float(grid1.max()),
            "grid_energy_kwh": float(grid1.sum() * DT_H),
        })
        save()

        print(
            "STAGE_1_OPTIMAL_F2_KW:",
            f2_star,
            flush=True,
        )

        # P2: preservar pico de P1 e minimizar energia.
        m.lex_peak_objective.deactivate()

        m.lex_peak_cap = p.Constraint(
            expr=m.annual_peak
                <= f2_star + args.epsilon_kw
        )
        m.obj.activate()

        print("STAGE_2_MIN_GRID_ENERGY", flush=True)
        t2 = time.perf_counter()
        solved2 = solver.solve(m, load_solutions=False)

        result["stage_2"] = {
            "termination": str(
                solved2.solver.termination_condition
            ),
            "elapsed_seconds": round(
                time.perf_counter() - t2, 3
            ),
        }

        if (
            solved2.solver.termination_condition
            != p.TerminationCondition.optimal
        ):
            result["status"] = "STAGE_1_ONLY_CERTIFIED"
            return

        m.solutions.load_from(solved2)

        grid2 = np.fromiter(
            (p.value(m.grid[t]) for t in m.T),
            dtype=float,
            count=N,
        )
        energy = np.fromiter(
            (p.value(m.bess_energy[t]) for t in m.S),
            dtype=float,
            count=N + 1,
        )

        result["stage_2"].update({
            "grid_peak_kw": float(grid2.max()),
            "grid_energy_kwh": float(grid2.sum() * DT_H),
            "peak_cap_kw": f2_star + args.epsilon_kw,
            "peak_cap_exceedance_kw": float(
                max(
                    0.0,
                    grid2.max() - (
                        f2_star + args.epsilon_kw
                    ),
                )
            ),
            "pcc_exceedance_kw": float(
                max(0.0, grid2.max() - PCC_KW)
            ),
            "soc_initial_kwh": float(energy[0]),
            "soc_terminal_kwh": float(energy[-1]),
            "soc_closure_residual_kwh": float(
                energy[-1] - energy[0]
            ),
            "bess_energy_min_kwh": float(energy.min()),
            "bess_energy_max_kwh": float(energy.max()),
        })

        result["status"] = "LEXICOGRAPHIC_OPTIMAL"

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

        print("ANNUAL_B_LEXICOGRAPHIC_RESULT", flush=True)
        print(
            json.dumps(result, indent=2, ensure_ascii=False),
            flush=True,
        )
        print("RESULT_FILE:", outfile, flush=True)


if __name__ == "__main__":
    main()
