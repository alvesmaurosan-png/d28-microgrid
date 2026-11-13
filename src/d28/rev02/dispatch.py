"""MILP energético REV02; cargas e custos devem vir de contratos externos verificados.

Este núcleo não substitui a logística individual nem o modelo de combustível.
"""
from .contracts import Scenario, contract


def build_energy_milp(*, scenario, year, load_kw, pv_pu, dt_hours,
                      pv_kw=0., bess_kwh=0., pcs_kw=0., chp_kw=0.,
                      grid_cap_kw=None, price_brl_kwh=None,
                      eta_charge=0.922, eta_discharge=0.922):
    import math
    spec = contract(scenario, year)
    s = spec.scenario
    if s == Scenario.C2:
        raise NotImplementedError("C2 requer modelo de serviço e combustível gasoso integrado; não reduzir a PV+BESS")
    if s == Scenario.REALISTA and any(x > 0 for x in (pv_kw, bess_kwh, pcs_kw, chp_kw)):
        raise ValueError("Realista não admite reforço local PV+BESS+CHP")
    if s == Scenario.BAU and grid_cap_kw is None:
        raise ValueError("BAU exige capacidade de rede e custo de reforço explícitos")
    if s == Scenario.C1 and chp_kw > 0:
        raise NotImplementedError("CHP exige contrato de combustível, eficiência e custo verificado")
    n = len(load_kw)
    if n == 0 or len(pv_pu) != n or (price_brl_kwh is not None and len(price_brl_kwh) != n):
        raise ValueError("Séries inconsistentes")
    seq = list(load_kw) + list(pv_pu) + (list(price_brl_kwh) if price_brl_kwh is not None else [])
    if any(not math.isfinite(float(x)) or float(x) < 0 for x in seq):
        raise ValueError("Séries negativas/não finitas")
    if dt_hours <= 0 or min(pv_kw, bess_kwh, pcs_kw, chp_kw) < 0:
        raise ValueError("Capacidades ou passo inválidos")
    if not (0 < eta_charge <= 1 and 0 < eta_discharge <= 1):
        raise ValueError("Eficiências inválidas")
    if pcs_kw > 0.55 * bess_kwh + 1e-8:
        raise ValueError("PCS incompatível com C-rate 0,55 provisório")
    cap = spec.pcc_limit_kw if spec.pcc_limit_kw is not None else grid_cap_kw
    if cap is None or cap <= 0:
        raise ValueError("Limite de importação inválido")
    import pyomo.environ as p
    m = p.ConcreteModel()
    m.T = p.RangeSet(0, n - 1)
    m.S = p.RangeSet(0, n)
    m.grid = p.Var(m.T, domain=p.NonNegativeReals, bounds=(0, cap))
    m.pv = p.Var(m.T, domain=p.NonNegativeReals)
    m.ch = p.Var(m.T, domain=p.NonNegativeReals)
    m.dis = p.Var(m.T, domain=p.NonNegativeReals)
    m.mode = p.Var(m.T, domain=p.Binary)
    m.soc = p.Var(m.S, bounds=(0.1*bess_kwh, 0.9*bess_kwh))
    m.pv_limit = p.Constraint(m.T, rule=lambda m,t: m.pv[t] <= pv_kw*float(pv_pu[t]))
    m.balance = p.Constraint(m.T, rule=lambda m,t: m.grid[t]+m.pv[t]+m.dis[t] == float(load_kw[t])+m.ch[t])
    m.ch_limit = p.Constraint(m.T, rule=lambda m,t: m.ch[t] <= pcs_kw*m.mode[t])
    m.dis_limit = p.Constraint(m.T, rule=lambda m,t: m.dis[t] <= pcs_kw*(1-m.mode[t]))
    m.soc_balance = p.Constraint(m.T, rule=lambda m,t: m.soc[t+1] == m.soc[t]+dt_hours*(eta_charge*m.ch[t]-m.dis[t]/eta_discharge))
    m.soc_initial = p.Constraint(expr=m.soc[0] == 0.5*bess_kwh)
    m.soc_terminal = p.Constraint(expr=m.soc[n] == m.soc[0])
    price = price_brl_kwh if price_brl_kwh is not None else [1.]*n
    m.obj = p.Objective(expr=sum(float(price[t])*dt_hours*m.grid[t] for t in m.T))
    m._rev02 = {"scenario":s.value,"year":year,"classification":"ENERGY_CORE_ONLY_NOT_INTEGRATED", "pcc_kw":cap}
    return m


def solve_energy_milp(model, solver="appsi_highs"):
    import math
    import pyomo.environ as p

    opt = p.SolverFactory(solver)

    if not opt.available(False):
        raise RuntimeError(f"Solver n?o dispon?vel: {solver}")

    try:
        res = opt.solve(model, load_solutions=False)
    except RuntimeError as exc:
        if "A feasible solution was not found" in str(exc):
            return {
                "status": "INFEASIBLE_OR_NOT_OPTIMAL",
                "termination": "NO_FEASIBLE_SOLUTION_REPORTED",
                "detail": str(exc),
            }
        raise

    termination = res.solver.termination_condition

    if termination != p.TerminationCondition.optimal:
        return {
            "status": "INFEASIBLE_OR_NOT_OPTIMAL",
            "termination": str(termination),
        }

    model.solutions.load_from(res)

    grid = []
    for t in model.T:
        value = float(p.value(model.grid[t]))
        if not math.isfinite(value) or value < -1e-6:
            raise ValueError("INVALID_GRID_KW")
        grid.append(max(0.0, value))

    objective = float(p.value(model.obj))

    if not math.isfinite(objective):
        raise ValueError("INVALID_OBJECTIVE")

    return {
        "status": "PASS_ENERGY_ONLY",
        "f2_kw": max(grid),
        "grid_kw": grid,
        "objective_brl": objective,
    }
