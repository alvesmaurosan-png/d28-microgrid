
import argparse
import json
import numpy as np
import pandas as pd

from pathlib import Path
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from d28.optimization.r0_nsga2_integrated import solve_lex

DAYS = (149, 183, 216, 279, 359)
PCC = 2500.0
DT = 0.25

class R0Multiday(ElementwiseProblem):
    def __init__(self, load, solar, limits):
        super().__init__(
            n_var=3, n_obj=2, n_ieq_constr=1,
            xl=np.zeros(3), xu=np.array(limits, dtype=float)
        )
        self.load = load
        self.solar = solar
        self.limits = np.array(limits, dtype=float)
        self.cache = {}
        self.stats = dict(
            evaluations=0, screen_rejected=0,
            milp_calls=0, milp_nonoptimal=0,
            feasible_evaluations=0
        )

    def _evaluate(self, x, out, *args, **kwargs):
        self.stats["evaluations"] += 1
        key = tuple(round(float(v), 8) for v in x)

        if key not in self.cache:
            pv, bess, pcs = map(float, x)

            excess = max(
                float(np.max(
                    self.load[d] - pv*self.solar[d] - pcs - PCC
                ))
                for d in DAYS
            )

            if excess > 1e-6:
                self.stats["screen_rejected"] += 1
                result = dict(
                    feasible=False, violation=excess,
                    peaks={}, reason="POWER_SCREEN"
                )
            else:
                peaks = {}
                result = None

                for d in DAYS:
                    self.stats["milp_calls"] += 1
                    r = solve_lex(
                        self.load[d], self.solar[d],
                        pv, bess, pcs, pcc_kw=PCC
                    )

                    if r is None:
                        self.stats["milp_nonoptimal"] += 1
                        result = dict(
                            feasible=False, violation=1.0,
                            peaks=peaks,
                            reason=f"MILP_NO_OPTIMUM_DAY_{d}"
                        )
                        break

                    peak = float(r["F2_kw"])
                    if not np.isfinite(peak) or peak > PCC + 1e-5:
                        raise RuntimeError(
                            f"Pico invalido no dia {d}: {peak}"
                        )
                    peaks[str(d)] = peak

                if result is None:
                    result = dict(
                        feasible=True, violation=0.0,
                        peaks=peaks,
                        max_peak=max(peaks.values()),
                        reason="ALL_DAYS_OPTIMAL"
                    )

            self.cache[key] = result

        r = self.cache[key]
        index = float(np.sum(x / self.limits))

        if r["feasible"]:
            self.stats["feasible_evaluations"] += 1
            out["F"] = [index, r["max_peak"]]
            out["G"] = [-1.0]
        else:
            out["F"] = [index, PCC + max(0, r["violation"])]
            out["G"] = [1.0 + max(0, r["violation"]) / PCC]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=24)
    ap.add_argument("--generations", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pv-max", type=float, default=10000)
    ap.add_argument("--bess-max", type=float, default=40000)
    ap.add_argument("--pcs-max", type=float, default=10000)
    args = ap.parse_args()

    if args.population < 4 or args.generations < 1:
        ap.error("Populacao >= 4 e geracoes >= 1")
    limits = [args.pv_max, args.bess_max, args.pcs_max]
    if any(v <= 0 for v in limits):
        ap.error("Limites devem ser positivos")

    source = Path(
        "data/processed/milp_inputs/R0_inputs_E100_15min.csv"
    )
    df = pd.read_csv(source)
    if len(df) != 35040:
        raise ValueError("Esperados 35040 intervalos")

    load = df["load_charging_ac_kw"].to_numpy(
        dtype=float
    ).reshape(365, 96)
    solar = df["pv_kw_per_kwp"].to_numpy(
        dtype=float
    ).reshape(365, 96)

    if (not np.isfinite(load).all()
        or not np.isfinite(solar).all()
        or np.any(load < 0)
        or np.any(solar < 0)):
        raise ValueError("Series de entrada invalidas")

    problem = R0Multiday(load, solar, limits)
    res = minimize(
        problem, NSGA2(pop_size=args.population),
        termination=("n_gen", args.generations),
        seed=args.seed, verbose=True
    )

    rows = []
    if res.X is not None:
        for x in np.atleast_2d(res.X):
            key = tuple(round(float(v), 8) for v in x)
            r = problem.cache.get(key)
            if r is None or not r["feasible"]:
                continue

            row = dict(
                pv_kwp=float(x[0]),
                bess_kwh=float(x[1]),
                pcs_kw=float(x[2]),
                size_index_NOT_F1=float(
                    np.sum(x / problem.limits)
                ),
                F2_multiday_max_kw=r["max_peak"],
                feasible_all_days=True
            )
            for d in DAYS:
                row[f"grid_peak_day_{d}_kw"] = r["peaks"][str(d)]
            rows.append(row)

    outdir = Path("results/r0_nsga2_multiday")
    outdir.mkdir(parents=True, exist_ok=True)

    columns = [
        "pv_kwp", "bess_kwh", "pcs_kw",
        "size_index_NOT_F1", "F2_multiday_max_kw",
        "feasible_all_days"
    ] + [f"grid_peak_day_{d}_kw" for d in DAYS]

    pd.DataFrame(rows, columns=columns).to_csv(
        outdir / "pareto_multiday.csv", index=False
    )

    summary = dict(
        status="MULTIDAY_EXPERIMENTAL_NOT_SCIENTIFIC",
        scenario="E100",
        days=list(DAYS),
        pcc_kw=PCC,
        dt_hours=DT,
        population=args.population,
        generations=args.generations,
        seed=args.seed,
        limits=dict(zip(["pv", "bess", "pcs"], limits)),
        counters=problem.stats,
        nondominated_feasible=len(rows),
        F1="NOT_COMPUTED",
        F3="NOT_COMPUTED",
        annual_feasibility="NOT_VALIDATED",
        result_csv=str(outdir / "pareto_multiday.csv")
    )

    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print("MULTIDAY_SUMMARY")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
