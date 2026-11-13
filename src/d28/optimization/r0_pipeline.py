
"""R0: integra??o cronol?gica MILP + indicadores + NSGA-II.

Pesquisa de otimiza??o; n?o constitui projeto executivo.
Fatores econ?micos e ACV devem ser fornecidos explicitamente.
"""
from pathlib import Path
import csv
import json
import math

import numpy as np
import pyomo.environ as p

from d28.dispatch.milp import build_r0_milp


REQUIRED = {
    "economic": [
        "pv_capex_brl_per_kwp",
        "bess_capex_brl_per_kwh",
        "pcs_capex_brl_per_kw",
        "annual_fixed_opex_fraction",
        "energy_tariff_brl_per_kwh",
        "annual_pkm",
        "discount_rate",
        "economic_horizon_years",
    ],
    "lca": [
        "pv_kgco2e_per_kwp",
        "bess_kgco2e_per_kwh",
        "pcs_kgco2e_per_kw",
        "grid_kgco2e_per_kwh",
        "replacement_kgco2e_total",
        "end_of_life_kgco2e_total",
    ],
}


def validate_assumptions(config):
    missing = [
        f"{section}.{name}"
        for section, names in REQUIRED.items()
        for name in names
        if config.get(section, {}).get(name) is None
    ]
    if missing:
        raise ValueError(
            "F1/F3 INCOMPLETAS. Preencher explicitamente: "
            + ", ".join(missing)
        )

    for section, names in REQUIRED.items():
        for name in names:
            value = float(config[section][name])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Parametro invalido: {section}.{name}")

    if config["economic"]["annual_pkm"] <= 0:
        raise ValueError("annual_pkm deve ser positivo")
    if config["economic"]["economic_horizon_years"] < 1:
        raise ValueError("Horizonte economico invalido")


def read_numeric_series(path, column):
    """L? coluna num?rica declarada, sem escolher colunas por adivinha??o."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        reader = csv.DictReader(f, dialect=dialect)

        if column not in (reader.fieldnames or []):
            raise ValueError(
                f"Coluna '{column}' ausente em {path.name}. "
                f"Disponiveis: {reader.fieldnames}"
            )

        values = []
        for row in reader:
            raw = row[column].strip()
            value = float(raw.replace(",", "."))
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Valor invalido em {path.name}")
            values.append(value)

    if not values:
        raise ValueError(f"Serie vazia: {path}")
    return np.asarray(values, dtype=float)


def prepare_series(load, solar, solar_resolution_minutes=60):
    """Alinha s?ries de 15 min, preservando energia por intervalo.

    A expans?o hor?ria em quatro intervalos ? zero-order hold:
    hip?tese expl?cita, n?o medi??o INMET de 15 min.
    """
    if solar_resolution_minutes == 60:
        if len(solar) != 8760:
            raise ValueError("Serie solar horaria deve ter 8760 pontos")
        solar = np.repeat(solar, 4)
    elif solar_resolution_minutes != 15:
        raise ValueError("Resolucao solar nao suportada")

    if len(load) != len(solar):
        raise ValueError(
            f"Desalinhamento: demanda={len(load)}, solar={len(solar)}. "
            "Nao combinar anos ou intervalos sem reconciliacao."
        )
    return load, solar


def solve_dispatch(load, solar, pv_kwp, bess_kwh, pcs_kw,
                   pcc_kw=2500.0, dt=0.25):
    """Despacho lexicogr?fico: pico primeiro, energia depois."""
    model = build_r0_milp(
        load_kw=load.tolist(),
        pv_pu=solar.tolist(),
        pv_capacity_kw=float(pv_kwp),
        bess_capacity_kwh=float(bess_kwh),
        pcs_power_kw=float(pcs_kw),
        pcc_cap_kw=float(pcc_kw),
        dt_hours=float(dt),
        terminal_policy="cyclic",
    )

    model.del_component(model.obj)
    model.peak = p.Var(domain=p.NonNegativeReals,
                       bounds=(0, float(pcc_kw)))
    model.peak_limit = p.Constraint(
        model.T, rule=lambda m, t: m.grid[t] <= m.peak
    )
    model.obj = p.Objective(expr=model.peak, sense=p.minimize)

    solver = p.SolverFactory("appsi_highs")
    if not solver.available():
        raise RuntimeError("HiGHS indisponivel")

    first = solver.solve(model, load_solutions=False)
    if first.solver.termination_condition != p.TerminationCondition.optimal:
        return None

    model.solutions.load_from(first)
    optimum_peak = float(p.value(model.peak))

    model.peak_fix = p.Constraint(
        expr=model.peak <= optimum_peak + 1e-5
    )
    model.del_component(model.obj)
    model.obj = p.Objective(
        expr=dt * sum(model.grid[t] for t in model.T),
        sense=p.minimize
    )

    second = solver.solve(model, load_solutions=False)
    if second.solver.termination_condition != p.TerminationCondition.optimal:
        return None

    model.solutions.load_from(second)
    grid = np.array([p.value(model.grid[t]) for t in model.T])

    return {
        "F2_kw": float(grid.max()),
        "grid_energy_kwh": float(grid.sum() * dt),
        "pcc_utilization": float(grid.max() / pcc_kw),
        "grid_series_kw": grid,
    }


def evaluate_objectives(design, dispatch, assumptions):
    """Calcula objetivos sob fronteira R0 declarada."""
    validate_assumptions(assumptions)

    pv, bess, pcs = map(float, design)
    e = assumptions["economic"]
    a = assumptions["lca"]

    capex = (
        pv * e["pv_capex_brl_per_kwp"]
        + bess * e["bess_capex_brl_per_kwh"]
        + pcs * e["pcs_capex_brl_per_kw"]
    )

    annual_opex = (
        capex * e["annual_fixed_opex_fraction"]
        + dispatch["grid_energy_kwh"]
        * e["energy_tariff_brl_per_kwh"]
    )

    years = int(e["economic_horizon_years"])
    rate = float(e["discount_rate"])
    discount_sum = sum(
        (1 + rate) ** (-year)
        for year in range(1, years + 1)
    )

    pkm_present_value = e["annual_pkm"] * discount_sum
    cost_present_value = capex + annual_opex * discount_sum

    f1 = cost_present_value / pkm_present_value
    f2 = dispatch["F2_kw"]

    embodied = (
        pv * a["pv_kgco2e_per_kwp"]
        + bess * a["bess_kgco2e_per_kwh"]
        + pcs * a["pcs_kgco2e_per_kw"]
        + a["replacement_kgco2e_total"]
        + a["end_of_life_kgco2e_total"]
    )
    operational = (
        dispatch["grid_energy_kwh"]
        * a["grid_kgco2e_per_kwh"]
        * years
    )
    f3 = (embodied + operational) / (e["annual_pkm"] * years)

    return [float(f1), float(f2), float(f3)]


def optimize_r0(load, solar, assumptions, bounds,
                population=12, generations=3, seed=42):
    """NSGA-II com MILP interno; or?amento inicial reduzido."""
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import ElementwiseProblem
    from pymoo.optimize import minimize

    validate_assumptions(assumptions)

    class R0Problem(ElementwiseProblem):
        def __init__(self):
            super().__init__(
                n_var=3,
                n_obj=3,
                n_ieq_constr=1,
                xl=np.asarray(bounds["lower"], dtype=float),
                xu=np.asarray(bounds["upper"], dtype=float),
            )

        def _evaluate(self, x, out, *args, **kwargs):
            pv, bess, pcs = map(float, x)
            out["G"] = [pcs - 0.55 * bess]

            if pcs > 0.55 * bess:
                out["F"] = [1e20, 1e20, 1e20]
                return

            result = solve_dispatch(load, solar, pv, bess, pcs)

            if result is None:
                out["G"] = [max(1.0, pcs - 0.55 * bess)]
                out["F"] = [1e20, 1e20, 1e20]
                return

            out["F"] = evaluate_objectives(
                (pv, bess, pcs), result, assumptions
            )

    algorithm = NSGA2(pop_size=population)

    result = minimize(
        R0Problem(),
        algorithm,
        termination=("n_gen", generations),
        seed=seed,
        verbose=True,
    )

    return result
