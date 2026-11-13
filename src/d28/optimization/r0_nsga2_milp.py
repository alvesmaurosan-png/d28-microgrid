
"""R0: NSGA-II externo + MILP econ?mico interno, biobjetivo explorat?rio."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyomo.environ as p
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize

from d28.dispatch.milp import build_r0_milp
from d28.economics.f1 import Economics
from d28.economics.milp_adapter import attach_economic_objective
from d28.objectives.r0_evaluator import evaluate_r0_model


def nondominated(values):
    values = np.asarray(values, dtype=float)
    keep = np.ones(len(values), dtype=bool)
    for i in range(len(values)):
        if np.any(np.all(values <= values[i], axis=1) &
                  np.any(values < values[i], axis=1)):
            keep[i] = False
    return keep


class R0Problem(ElementwiseProblem):
    def __init__(self, load, solar, months, cfg, dt, bounds,
                 peak_range, solver_name="appsi_highs"):
        self.load = np.asarray(load, dtype=float)
        self.solar = np.asarray(solar, dtype=float)
        self.months = list(months)
        self.cfg = cfg
        self.dt = float(dt)
        self.peak_range = tuple(peak_range)
        self.pcs_max = float(bounds[2][1])
        self.solver_name = solver_name
        self.history = []
        self.cache = {}

        super().__init__(
            n_var=4,
            n_obj=2,
            n_ieq_constr=0,
            xl=np.asarray([
                bounds[0][0],
                bounds[1][0],
                0.0,
                0.0,
            ], dtype=float),
            xu=np.asarray([
                bounds[0][1],
                bounds[1][1],
                1.0,
                1.0,
            ], dtype=float),
        )

    def _evaluate(self, x, out, *args, **kwargs):
        pv, bess, pcs_fraction, alpha = map(float, x)

        peak_limit = (
            self.peak_range[0] +
            alpha * (self.peak_range[1] - self.peak_range[0])
        )

        pv_available = np.maximum(self.solar, 0.0) * pv

        required_bess_power = np.maximum(
            self.load - pv_available - peak_limit,
            0.0,
        )

        pcs_min = float(required_bess_power.max())
        pcs_upper = min(self.pcs_max, 0.55 * bess)

        if pcs_min <= pcs_upper:
            pcs = pcs_min + pcs_fraction * (
                pcs_upper - pcs_min
            )
        else:
            pcs = pcs_upper
        key = tuple(round(v, 6) for v in x)

        if key in self.cache:
            out["F"] = self.cache[key]
            return

        row = {
            "pv_kwp": pv,
            "bess_kwh": bess,
            "pcs_kw": pcs,
            "peak_limit_kw": peak_limit,
            "status": "NOT_SOLVED",
        }

        try:
            if pcs_min > pcs_upper + 1e-6:
                raise RuntimeError(
                    "INFEASIBLE_DESIGN_EQ008: "
                    f"pcs_required={pcs_min:.3f}kW, "
                    f"pcs_allowed={pcs_upper:.3f}kW"
                )

            model = build_r0_milp(
                load_kw=self.load.tolist(),
                pv_pu=self.solar.tolist(),
                pv_capacity_kw=pv,
                bess_capacity_kwh=bess,
                pcs_power_kw=pcs,
                pcc_cap_kw=self.cfg.pcc_import_limit_kw,
                dt_hours=self.dt,
                initial_soc=0.5,
                terminal_policy="cyclic",
            )

            # Restri??o epsilon para F2.
            model.peak_epsilon = p.Constraint(
                model.T,
                rule=lambda m, t: m.grid[t] <= peak_limit,
            )

            attach_economic_objective(
                model,
                self.cfg,
                pv_kwp=pv,
                bess_kwh=bess,
                pcs_kw=pcs,
                months=self.months,
                dt_hours=self.dt,
            )


            if self.solver_name == "appsi_highs":
                from pyomo.contrib.appsi.solvers import Highs

                solver = Highs()
                solver.config.load_solution = False
                solver.config.time_limit = 600

                if not solver.available():
                    raise RuntimeError("SOLVER_UNAVAILABLE")

                result = solver.solve(model)

                term = result.termination_condition

                row["solver_termination"] = str(term)
                row["solver_best_feasible_objective"] = str(
                    result.best_feasible_objective
                )

                if str(term).lower().split(".")[-1] != "optimal":
                    raise RuntimeError(
                        f"MILP_TERMINATION_{term}"
                    )

                solver.load_vars()

            else:
                solver = p.SolverFactory(self.solver_name)

                if not solver.available(False):
                    raise RuntimeError("SOLVER_UNAVAILABLE")

                result = solver.solve(
                    model,
                    tee=False,
                    load_solutions=False,
                )

                term = result.solver.termination_condition
                row["solver_termination"] = str(term)

                if term != p.TerminationCondition.optimal:
                    raise RuntimeError(
                        f"MILP_TERMINATION_{term}"
                    )

                model.solutions.load_from(result)


            evaluated = evaluate_r0_model(
                model,
                self.cfg,
                load_kw=self.load,
                pv_pu=self.solar,
                pv_kwp=pv,
                bess_kwh=bess,
                pcs_kw=pcs,
                months=self.months,
                dt_hours=self.dt,
            )

            if not evaluated["objectives_evaluated"]:
                raise RuntimeError(
                    "DISPATCH_REJECTED_" + evaluated["status"]
                )

            objectives = evaluated["objectives"]
            f1 = float(objectives["f1_present_value_brl"])
            f2 = float(objectives["f2_peak_kw"])

            if not np.isfinite([f1, f2]).all():
                raise RuntimeError("NONFINITE_OBJECTIVES")

            out["F"] = [f1, f2]
            row.update(
                status="OPTIMAL_MILP",
                f1_brl=f1,
                f2_kw=f2,
            )

        except Exception as exc:
            # Penalidade expl?cita: nunca classificar falha como fact?vel.
            out["F"] = [1e15, 1e9]
            row["status"] = "FAILED"
            row["error"] = str(exc)

        self.history.append(row)
        self.cache[key] = list(out["F"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--economics", default=
        "config/economics/r0_f1_exploratory_2026.json")
    parser.add_argument("--output", default="results/r0_nsga2_milp")
    parser.add_argument("--intervals", type=int, default=96)
    parser.add_argument("--population", type=int, default=12)
    parser.add_argument("--generations", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--annual", action="store_true")
    parser.add_argument("--solver", default="appsi_highs")
    parser.add_argument("--pv-max", type=float, default=1000.0)
    parser.add_argument("--bess-max", type=float, default=30000.0)
    parser.add_argument("--pcs-max", type=float, default=5000.0)
    args = parser.parse_args()

    if args.annual and args.intervals != 35040:
        parser.error("Modo anual exige --intervals 35040")
    if args.intervals <= 0:
        parser.error("N?mero de intervalos inv?lido")

    df = pd.read_csv(args.input, nrows=args.intervals)
    if len(df) != args.intervals:
        parser.error("Arquivo cont?m menos intervalos que o solicitado")

    required = [
        "load_charging_ac_kw",
        "pv_kw_per_kwp",
        "interval_start_local",
    ]
    missing = [c for c in required if c not in df]
    if missing:
        parser.error(f"Colunas ausentes: {missing}")

    load = df["load_charging_ac_kw"].to_numpy(dtype=float)
    solar = df["pv_kw_per_kwp"].to_numpy(dtype=float)
    months = pd.to_datetime(
        df["interval_start_local"]
    ).dt.month.tolist()

    dt = 0.25
    if "dt_hours" in df:
        if not np.allclose(df["dt_hours"], dt):
            parser.error("Intervalos temporais n?o uniformes")

    cfg = Economics.from_json(args.economics)
    peak_max = float(cfg.pcc_import_limit_kw)

    if not np.isfinite(load).all() or not np.isfinite(solar).all():
        parser.error("Entradas n?o finitas")

    if args.population < 4 or args.generations < 1:
        parser.error("Popula??o/gera??es inv?lidas")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    problem = R0Problem(
        load, solar, months, cfg, dt,
        bounds=[
            (0.0, args.pv_max),
            (0.0, args.bess_max),
            (0.0, args.pcs_max),
        ],
        peak_range=(0.0, peak_max),
        solver_name=args.solver,
    )

    algorithm = NSGA2(pop_size=args.population)
    result = minimize(
        problem,
        algorithm,
        termination=("n_gen", args.generations),
        seed=args.seed,
        verbose=True,
    )

    history = pd.DataFrame(problem.history)
    history.to_csv(output / "evaluations.csv", index=False)

    valid = history.loc[
        history["status"] == "OPTIMAL_MILP"
    ].copy()

    if len(valid):
        mask = nondominated(
            valid[["f1_brl", "f2_kw"]].to_numpy()
        )
        front = valid.loc[mask].sort_values(
            ["f1_brl", "f2_kw"]
        )
        front.to_csv(output / "pareto_F1_F2.csv", index=False)

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 6))
        ax.scatter(
            valid["f2_kw"], valid["f1_brl"] / 1e6,
            alpha=0.35, label="Solu??es fact?veis"
        )
        ax.scatter(
            front["f2_kw"], front["f1_brl"] / 1e6,
            label="N?o dominadas"
        )
        ax.set_xlabel("F2 ? Pico de importa??o (kW)")
        ax.set_ylabel("F1 ? Valor presente (milh?es de R$)")
        ax.set_title("R0 ? Fronteira F1 ? F2 (explorat?ria)")
        ax.legend()
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(output / "pareto_F1_F2.png", dpi=180)
        plt.close(fig)

    manifest = {
        "architecture": "R0",
        "mode": "annual" if args.annual else "pilot",
        "intervals": args.intervals,
        "population": args.population,
        "generations": args.generations,
        "seed": args.seed,
        "inner_dispatch_policy": "economic_MILP_epsilon_peak",
        "f3_status": "PENDING_LCA_VALIDATION",
        "scientific_triobjective_certified": False,
        "evaluations": len(history),
        "feasible_evaluations": len(valid),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print("R0_ORCHESTRATION_FINISHED", manifest)


if __name__ == "__main__":
    main()
