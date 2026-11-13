"""M3.6.1 ? Avaliador f?sico-econ?mico R0.

Avalia despacho previamente resolvido.
N?o executa MILP, n?o calcula F3 e n?o executa NSGA-II.
"""

from collections.abc import Sequence
import math

from d28.economics.f1 import Economics, annual_bill, present_value


def evaluate_r0(
    cfg: Economics,
    *,
    pv_kwp: float,
    bess_kwh: float,
    pcs_kw: float,
    grid_kw: Sequence[float],
    months: Sequence[int],
    dt_hours: float,
    annual_pkm: float | None = None,
) -> dict:
    """Retorna F1, F2 e a contabiliza??o econ?mica audit?vel."""

    grid = [float(x) for x in grid_kw]
    month_vector = [int(x) for x in months]

    if not grid:
        raise ValueError("S?rie de despacho vazia")

    if len(grid) != len(month_vector):
        raise ValueError("Comprimentos incompat?veis")

    if not all(math.isfinite(x) for x in grid):
        raise ValueError("Importa??o cont?m valores n?o finitos")

    bill = annual_bill(
        cfg,
        grid_kw=grid,
        dt_hours=float(dt_hours),
        months=month_vector,
    )

    economic = present_value(
        cfg,
        pv_kwp=float(pv_kwp),
        bess_kwh=float(bess_kwh),
        pcs_kw=float(pcs_kw),
        annual_variable_bill_brl=bill["total_variable_bill_brl"],
        annual_pkm=annual_pkm,
    )

    f2 = max(grid)

    return {
        "status": "EVALUATED_DISPATCH",
        "architecture": "R0",
        "f1_present_value_brl": economic["pv_total_cost_brl"],
        "f1_brl_per_pkm": economic["f1_brl_per_pkm"],
        "f2_peak_kw": f2,
        "f3": None,
        "f3_status": "PENDING_LCA_VALIDATION",
        "grid_energy_kwh": bill["energy_kwh"],
        "annual_energy_cost_brl": bill["energy_cost_brl"],
        "annual_demand_cost_brl": bill["demand_cost_brl"],
        "monthly_peak_kw": bill["monthly_peak_kw"],
        "annual_variable_bill_brl": bill["total_variable_bill_brl"],
        "initial_capex_brl": economic["initial_capex_brl"],
        "annual_fixed_opex_brl": economic["annual_fixed_opex_brl"],
        "replacement_present_value_brl":
            economic["replacement_present_value_brl"],
        "annuity_factor": economic["annuity_factor"],
        "dispatch_policy": "EXTERNALLY_SPECIFIED",
        "scientific_triobjective_certified": False,
    }


def verify_r0_dispatch(
    *,
    load_kw,
    pv_kw,
    grid_kw,
    bess_charge_kw,
    bess_discharge_kw,
    bess_energy_kwh,
    bess_capacity_kwh,
    pcs_kw,
    pcc_kw,
    dt_hours,
    eta_charge=0.922,
    eta_discharge=0.922,
    soc_min=0.10,
    soc_max=0.90,
    tolerance=1e-5,
):
    """Verifica??o independente de balan?os e limites do despacho R0."""
    import numpy as np

    arrays = {
        "load": np.asarray(load_kw, dtype=float),
        "pv": np.asarray(pv_kw, dtype=float),
        "grid": np.asarray(grid_kw, dtype=float),
        "charge": np.asarray(bess_charge_kw, dtype=float),
        "discharge": np.asarray(bess_discharge_kw, dtype=float),
        "energy": np.asarray(bess_energy_kwh, dtype=float),
    }

    n = len(arrays["grid"])
    if n == 0 or any(
        len(arrays[k]) != n
        for k in ("load", "pv", "charge", "discharge")
    ) or len(arrays["energy"]) != n + 1:
        raise ValueError("Dimens?es das s?ries incompat?veis")

    if any(not np.isfinite(a).all() for a in arrays.values()):
        raise ValueError("S?ries cont?m valores n?o finitos")

    if not all(
        math.isfinite(float(x))
        for x in (
            bess_capacity_kwh, pcs_kw, pcc_kw, dt_hours,
            eta_charge, eta_discharge, soc_min, soc_max, tolerance
        )
    ):
        raise ValueError("Par?metros n?o finitos")

    if (
        bess_capacity_kwh <= 0 or pcs_kw < 0 or pcc_kw <= 0
        or dt_hours <= 0 or not 0 < eta_charge <= 1
        or not 0 < eta_discharge <= 1
        or not 0 <= soc_min < soc_max <= 1
        or tolerance < 0
    ):
        raise ValueError("Par?metros f?sicos inv?lidos")

    a = arrays
    balance = (
        a["grid"] + a["pv"] + a["discharge"]
        - a["load"] - a["charge"]
    )

    transition = (
        a["energy"][1:] - a["energy"][:-1]
        - dt_hours * (
            eta_charge * a["charge"]
            - a["discharge"] / eta_discharge
        )
    )

    def upper_violation(values, bound):
        return float(max(0.0, np.max(values - bound)))

    def lower_violation(values, bound=0.0):
        return float(max(0.0, np.max(bound - values)))

    residuals = {
        "balance_kw": float(np.max(np.abs(balance))),
        "soc_transition_kwh": float(np.max(np.abs(transition))),
        "soc_cyclic_kwh": float(abs(a["energy"][-1] - a["energy"][0])),
        "pcc_upper_kw": upper_violation(a["grid"], pcc_kw),
        "grid_negative_kw": lower_violation(a["grid"]),
        "charge_upper_kw": upper_violation(a["charge"], pcs_kw),
        "discharge_upper_kw": upper_violation(a["discharge"], pcs_kw),
        "charge_negative_kw": lower_violation(a["charge"]),
        "discharge_negative_kw": lower_violation(a["discharge"]),
        "pv_negative_kw": lower_violation(a["pv"]),
        "load_negative_kw": lower_violation(a["load"]),
        "soc_lower_kwh": lower_violation(
            a["energy"], soc_min * bess_capacity_kwh
        ),
        "soc_upper_kwh": upper_violation(
            a["energy"], soc_max * bess_capacity_kwh
        ),
        "simultaneous_charge_discharge_kw": float(
            np.max(np.minimum(a["charge"], a["discharge"]))
        ),
        "pcs_design_limit_kw": float(
            max(0.0, pcs_kw - 0.55 * bess_capacity_kwh)
        ),
    }

    passed = all(v <= tolerance for v in residuals.values())

    return {
        "status": "PHYSICALLY_FEASIBLE" if passed else "PHYSICAL_VIOLATION",
        "passed": passed,
        "intervals": n,
        "tolerance": tolerance,
        "residuals": residuals,
    }


def verify_r0_pv_balance(
    *,
    pv_used_kw,
    pv_curtailed_kw,
    pv_available_kw,
    tolerance=1e-5,
):
    """Verifica conserva??o da gera??o fotovoltaica e n?o negatividade."""
    import numpy as np

    used = np.asarray(pv_used_kw, dtype=float)
    curtailed = np.asarray(pv_curtailed_kw, dtype=float)
    available = np.asarray(pv_available_kw, dtype=float)

    if (
        used.ndim != 1
        or curtailed.ndim != 1
        or available.ndim != 1
        or len(used) == 0
        or len(used) != len(curtailed)
        or len(used) != len(available)
    ):
        raise ValueError("Dimens?es fotovoltaicas incompat?veis")

    if not all(np.isfinite(a).all() for a in (used, curtailed, available)):
        raise ValueError("S?ries fotovoltaicas n?o finitas")

    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Toler?ncia inv?lida")

    residuals = {
        "pv_balance_kw": float(
            np.max(np.abs(used + curtailed - available))
        ),
        "pv_used_negative_kw": float(max(0.0, -used.min())),
        "pv_curtailed_negative_kw": float(max(0.0, -curtailed.min())),
        "pv_available_negative_kw": float(max(0.0, -available.min())),
    }

    passed = all(value <= tolerance for value in residuals.values())

    return {
        "status": "PV_BALANCE_OK" if passed else "PV_BALANCE_VIOLATION",
        "passed": passed,
        "intervals": len(used),
        "residuals": residuals,
    }


def extract_r0_solution(model, *, pv_capacity_kw: float) -> dict:
    """Extrai s?ries de uma solu??o Pyomo R0 previamente carregada.

    N?o executa o solver. Rejeita vari?veis sem valores atribu?dos.
    """
    import numpy as np
    import pyomo.environ as p

    names = (
        "grid", "pv", "pv_curt",
        "bess_charge", "bess_discharge", "bess_energy",
    )
    for name in names:
        if not hasattr(model, name):
            raise ValueError(f"Componente ausente: {name}")

    if not math.isfinite(float(pv_capacity_kw)) or pv_capacity_kw < 0:
        raise ValueError("Capacidade FV inv?lida")

    time_index = list(model.T)
    state_index = list(model.S)

    if not time_index or len(state_index) != len(time_index) + 1:
        raise ValueError("?ndices temporais incompat?veis")

    def series(component, index, name):
        values = []
        for t in index:
            value = p.value(component[t], exception=False)
            if value is None:
                raise ValueError(f"Vari?vel sem solu??o: {name}[{t}]")
            values.append(float(value))
        result = np.asarray(values, dtype=float)
        if not np.isfinite(result).all():
            raise ValueError(f"Valores n?o finitos: {name}")
        return result

    grid = series(model.grid, time_index, "grid")
    pv = series(model.pv, time_index, "pv")
    pv_curt = series(model.pv_curt, time_index, "pv_curt")
    charge = series(model.bess_charge, time_index, "bess_charge")
    discharge = series(model.bess_discharge, time_index, "bess_discharge")
    energy = series(model.bess_energy, state_index, "bess_energy")

    return {
        "grid_kw": grid,
        "pv_used_kw": pv,
        "pv_curtailed_kw": pv_curt,
        "bess_charge_kw": charge,
        "bess_discharge_kw": discharge,
        "bess_energy_kwh": energy,
        "intervals": len(time_index),
        "solution_loaded": True,
        "solver_executed_by_extractor": False,
    }


def evaluate_r0_model(
    model,
    cfg: Economics,
    *,
    load_kw,
    pv_pu,
    pv_kwp: float,
    bess_kwh: float,
    pcs_kw: float,
    months,
    dt_hours: float,
    annual_pkm: float | None = None,
    tolerance: float = 1e-5,
) -> dict:
    """Avalia valores carregados em um modelo Pyomo R0.

    N?o executa solver. Factibilidade f?sica n?o certifica otimalidade.
    """
    import numpy as np

    solution = extract_r0_solution(
        model, pv_capacity_kw=pv_kwp
    )

    load = np.asarray(load_kw, dtype=float)
    solar = np.asarray(pv_pu, dtype=float)

    n = solution["intervals"]

    if (
        load.ndim != 1
        or solar.ndim != 1
        or len(load) != n
        or len(solar) != n
        or not np.isfinite(load).all()
        or not np.isfinite(solar).all()
    ):
        raise ValueError("Entradas f?sicas incompat?veis")

    physical = verify_r0_dispatch(
        load_kw=load,
        pv_kw=solution["pv_used_kw"],
        grid_kw=solution["grid_kw"],
        bess_charge_kw=solution["bess_charge_kw"],
        bess_discharge_kw=solution["bess_discharge_kw"],
        bess_energy_kwh=solution["bess_energy_kwh"],
        bess_capacity_kwh=bess_kwh,
        pcs_kw=pcs_kw,
        pcc_kw=cfg.pcc_import_limit_kw,
        dt_hours=dt_hours,
        tolerance=tolerance,
    )

    photovoltaic = verify_r0_pv_balance(
        pv_used_kw=solution["pv_used_kw"],
        pv_curtailed_kw=solution["pv_curtailed_kw"],
        pv_available_kw=float(pv_kwp) * solar,
        tolerance=tolerance,
    )

    parameter_identity = verify_r0_parameter_identity(
        model,
        load_kw=load,
        pv_pu=solar,
        pv_kwp=pv_kwp,
        bess_kwh=bess_kwh,
        pcs_kw=pcs_kw,
        pcc_kw=cfg.pcc_import_limit_kw,
        dt_hours=dt_hours,
        tolerance=tolerance,
    )

    pyomo_audit = verify_r0_pyomo_constraints(
        model, tolerance=tolerance
    )

    if not (
        physical["passed"]
        and photovoltaic["passed"]
        and pyomo_audit["passed"]
        and parameter_identity["passed"]
    ):
        return {
            "status": "INFEASIBLE_DISPATCH_VALUES",
            "physical": physical,
            "photovoltaic": photovoltaic,
            "pyomo_audit": pyomo_audit,
            "parameter_identity": parameter_identity,
            "objectives_evaluated": False,
            "solver_optimality_certified": False,
        }

    objectives = evaluate_r0(
        cfg,
        pv_kwp=pv_kwp,
        bess_kwh=bess_kwh,
        pcs_kw=pcs_kw,
        grid_kw=solution["grid_kw"],
        months=months,
        dt_hours=dt_hours,
        annual_pkm=annual_pkm,
    )

    return {
        "status": "FEASIBLE_DISPATCH_EVALUATED",
        "physical": physical,
        "photovoltaic": photovoltaic,
        "pyomo_audit": pyomo_audit,
        "parameter_identity": parameter_identity,
        "objectives_evaluated": True,
        "objectives": objectives,
        "solver_optimality_certified": False,
    }


def verify_r0_pyomo_constraints(model, *, tolerance=1e-5) -> dict:
    """Audita restri??es ativas e dom?nios das vari?veis Pyomo.

    N?o executa solver e n?o certifica otimalidade.
    """
    import pyomo.environ as p

    if not math.isfinite(float(tolerance)) or tolerance < 0:
        raise ValueError("Toler?ncia inv?lida")

    residuals = {}
    failures = []
    checked_constraints = 0
    checked_variables = 0

    for component in model.component_objects(p.Constraint, active=True):
        max_violation = 0.0

        for index in component:
            constraint = component[index]
            if not constraint.active:
                continue

            body = p.value(constraint.body, exception=False)
            if body is None or not math.isfinite(float(body)):
                failures.append(f"{constraint.name}: valor indispon?vel")
                continue

            violation = 0.0

            if constraint.has_lb():
                lb = p.value(constraint.lower, exception=False)
                if lb is None or not math.isfinite(float(lb)):
                    failures.append(f"{constraint.name}: limite inferior inv?lido")
                    continue
                violation = max(violation, float(lb) - float(body))

            if constraint.has_ub():
                ub = p.value(constraint.upper, exception=False)
                if ub is None or not math.isfinite(float(ub)):
                    failures.append(f"{constraint.name}: limite superior inv?lido")
                    continue
                violation = max(violation, float(body) - float(ub))

            max_violation = max(max_violation, violation)
            checked_constraints += 1

        residuals[component.name] = max_violation

    max_domain_violation = 0.0

    for variable in model.component_data_objects(p.Var, active=True):
        value = p.value(variable, exception=False)

        if value is None or not math.isfinite(float(value)):
            failures.append(f"{variable.name}: valor indispon?vel")
            continue

        value = float(value)
        checked_variables += 1

        if variable.has_lb():
            max_domain_violation = max(
                max_domain_violation,
                float(variable.lb) - value
            )

        if variable.has_ub():
            max_domain_violation = max(
                max_domain_violation,
                value - float(variable.ub)
            )

        if variable.is_binary():
            max_domain_violation = max(
                max_domain_violation,
                abs(value - round(value))
            )

        elif variable.is_integer():
            max_domain_violation = max(
                max_domain_violation,
                abs(value - round(value))
            )

    residuals["variable_domains"] = max_domain_violation

    passed = (
        not failures
        and checked_constraints > 0
        and checked_variables > 0
        and all(value <= tolerance for value in residuals.values())
    )

    return {
        "status": "PYOMO_CONSTRAINTS_OK" if passed
                  else "PYOMO_CONSTRAINTS_VIOLATION",
        "passed": passed,
        "checked_constraints": checked_constraints,
        "checked_variables": checked_variables,
        "residuals": residuals,
        "failures": failures,
        "solver_executed": False,
    }


def verify_r0_parameter_identity(
    model,
    *,
    load_kw,
    pv_pu,
    pv_kwp,
    bess_kwh,
    pcs_kw,
    pcc_kw,
    dt_hours,
    tolerance=1e-6,
) -> dict:
    """Compara entradas externas com par?metros incorporados ao MILP R0.

    N?o executa solver nem modifica valores das vari?veis.
    """
    import numpy as np
    import pyomo.environ as p

    if not math.isfinite(float(tolerance)) or tolerance < 0:
        raise ValueError("Toler?ncia inv?lida")

    indices = list(model.T)
    n = len(indices)

    external_load = np.asarray(load_kw, dtype=float)
    external_solar = np.asarray(pv_pu, dtype=float)

    if (
        external_load.ndim != 1
        or external_solar.ndim != 1
        or len(external_load) != n
        or len(external_solar) != n
        or not np.isfinite(external_load).all()
        or not np.isfinite(external_solar).all()
    ):
        raise ValueError("S?ries externas inv?lidas")

    model_load = np.asarray(
        [p.value(model.load_kw[t]) for t in indices],
        dtype=float,
    )
    model_solar = np.asarray(
        [p.value(model.pv_pu[t]) for t in indices],
        dtype=float,
    )

    residuals = {
        "load_kw": float(np.max(np.abs(external_load - model_load))),
        "pv_pu": float(np.max(np.abs(external_solar - model_solar))),
    }

    metadata = getattr(model, "_r0_metadata", {})
    model_dt = metadata.get("dt_hours")

    if model_dt is None:
        raise ValueError("dt_hours ausente dos metadados")

    residuals["dt_hours"] = abs(float(dt_hours) - float(model_dt))

    grid_ub = model.grid[indices[0]].ub
    if grid_ub is None:
        raise ValueError("Limite PCC ausente")

    residuals["pcc_kw"] = abs(float(pcc_kw) - float(grid_ub))

    state_indices = list(model.S)
    if not state_indices:
        raise ValueError("Estados BESS ausentes")

    state = model.bess_energy[state_indices[0]]

    if state.lb is None or state.ub is None:
        raise ValueError("Limites SOC ausentes")

    residuals["bess_min_kwh"] = abs(
        float(state.lb) - 0.10 * float(bess_kwh)
    )
    residuals["bess_max_kwh"] = abs(
        float(state.ub) - 0.90 * float(bess_kwh)
    )

    # Identidade de FV e PCS ? verificada por coeficientes
    # das express?es lineares, sem alterar vari?veis.
    from pyomo.repn.standard_repn import generate_standard_repn

    def coefficient(expression, variable):
        repn = generate_standard_repn(expression)
        for var, coef in zip(
            repn.linear_vars or [],
            repn.linear_coefs or [],
        ):
            if var is variable:
                return float(p.value(coef))
        raise ValueError(
            f"Vari?vel {variable.name} ausente da express?o"
        )

    t = indices[0]

    # pv + pv_curt == pv_kwp * pv_pu
    # Para recuperar FV, utilizar intervalo com pv_pu != 0.
    solar_indices = [
        i for i in indices
        if abs(float(p.value(model.pv_pu[i]))) > tolerance
    ]

    if solar_indices:
        i = solar_indices[0]
        constraint = model.pv_accounting[i]
        available = float(p.value(constraint.lower))
        inferred_pv = available / float(p.value(model.pv_pu[i]))
        residuals["pv_kwp"] = abs(inferred_pv - float(pv_kwp))
        pv_identifiable = True
    else:
        residuals["pv_kwp"] = None
        pv_identifiable = False

    charge_constraint = model.bess_charge_limit[t]
    discharge_constraint = model.bess_discharge_limit[t]

    charge_repn = generate_standard_repn(charge_constraint.body)
    discharge_repn = generate_standard_repn(discharge_constraint.body)

    charge_mode_coef = coefficient(
        charge_constraint.body, model.bess_mode[t]
    )
    discharge_mode_coef = coefficient(
        discharge_constraint.body, model.bess_mode[t]
    )

    residuals["pcs_charge_kw"] = abs(
        abs(charge_mode_coef) - float(pcs_kw)
    )
    residuals["pcs_discharge_kw"] = abs(
        abs(discharge_mode_coef) - float(pcs_kw)
    )

    comparable = [
        value for value in residuals.values()
        if value is not None
    ]

    passed = (
        pv_identifiable
        and all(value <= tolerance for value in comparable)
    )

    return {
        "status": (
            "PARAMETER_IDENTITY_OK"
            if passed else "PARAMETER_IDENTITY_VIOLATION"
        ),
        "passed": passed,
        "intervals": n,
        "pv_capacity_identifiable": pv_identifiable,
        "residuals": residuals,
        "solver_executed": False,
    }
