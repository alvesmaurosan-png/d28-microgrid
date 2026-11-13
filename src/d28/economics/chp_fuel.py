"""Conditional natural-gas fuel accounting for D28 R1.

Fuel volumes are expressed in Nm3 per dispatch interval.
Prices are explicit inputs; no tariff is scientifically homologated here.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def natural_gas_cost(
    fuel_nm3: Sequence[float],
    price_brl_per_nm3: float,
) -> float:
    """Return total natural-gas cost in BRL for the supplied intervals."""
    price = float(price_brl_per_nm3)

    if not math.isfinite(price) or price < 0:
        raise ValueError("Gas price must be finite and nonnegative")

    volumes = list(fuel_nm3)

    if not volumes:
        raise ValueError("Fuel volume series must not be empty")

    total_volume = 0.0

    for index, value in enumerate(volumes):
        volume = float(value)

        if not math.isfinite(volume) or volume < 0:
            raise ValueError(
                f"Invalid fuel volume at interval {index}"
            )

        total_volume += volume

    return total_volume * price


def natural_gas_cost_from_solved_model(
    model,
    price_brl_per_nm3: float,
    *,
    solver_result,
) -> float:
    """Account for R1 fuel only after a confirmed optimal MILP solution."""
    import pyomo.environ as p
    from pyomo.opt import SolverStatus, TerminationCondition

    if solver_result is None:
        raise ValueError("Solver result is required")

    if (
        solver_result.solver.status != SolverStatus.ok
        or solver_result.solver.termination_condition
        != TerminationCondition.optimal
    ):
        raise ValueError("An optimal solver result is required")

    metadata = getattr(model, "_r0_metadata", {})
    if metadata.get("architecture") != "R1":
        raise ValueError("Expected an R1 model")

    if not hasattr(model, "chp") or not hasattr(model.chp, "fuel_nm3"):
        raise ValueError("R1 CHP fuel variable is missing")

    volumes = []

    for t in model.T:
        value = p.value(model.chp.fuel_nm3[t], exception=False)

        if value is None:
            raise ValueError(f"Undefined CHP fuel volume at interval {t}")

        volumes.append(value)

    return natural_gas_cost(volumes, price_brl_per_nm3)
