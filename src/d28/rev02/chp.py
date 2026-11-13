"""REV02.1 M5 — CHP elétrico incremental, sintético, sem homologação D28.

Acopla CHP ao modelo M1–M3 sem modificar seus arquivos originais.
O calor recuperado é contabilizado, mas NÃO recebe crédito econômico sem demanda
útil e integração térmica demonstradas.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class CHPParameters:
    electric_efficiency: float
    fuel_brl_per_kwh_lhv: float
    variable_om_brl_per_kwh_e: float
    availability: tuple[bool, ...]
    minimum_load_fraction: float = 0.0
    heat_recovery_fraction_lhv: float = 0.0
    fuel_limit_kwh_lhv: float | None = None


def attach_chp(model, *, capacity_kw: float, parameters: CHPParameters, dt_hours: float):
    """Adiciona geração, combustível, custo e limites ao MILP operacional existente.

    Importante: o modelo-base possui igualdade elétrica sem exportação. A geração
    CHP deve ser consumida localmente ou desligada; não há exportação implícita.
    """
    import pyomo.environ as p
    if hasattr(model, 'chp_generation'):
        raise ValueError('CHP já anexado ao modelo')
    n = len(model.T)
    values = (capacity_kw, dt_hours, parameters.electric_efficiency,
              parameters.fuel_brl_per_kwh_lhv, parameters.variable_om_brl_per_kwh_e,
              parameters.minimum_load_fraction, parameters.heat_recovery_fraction_lhv)
    if any(not isfinite(float(v)) for v in values):
        raise ValueError('Parâmetros CHP não finitos')
    if capacity_kw < 0 or dt_hours <= 0 or not 0 < parameters.electric_efficiency <= 1:
        raise ValueError('Capacidade, passo ou eficiência CHP inválidos')
    if parameters.fuel_brl_per_kwh_lhv < 0 or parameters.variable_om_brl_per_kwh_e < 0:
        raise ValueError('Custos CHP negativos')
    if not 0 <= parameters.minimum_load_fraction <= 1:
        raise ValueError('Carga mínima CHP inválida')
    if not 0 <= parameters.heat_recovery_fraction_lhv <= 1 - parameters.electric_efficiency + 1e-9:
        raise ValueError('Recuperação térmica excede energia disponível')
    if len(parameters.availability) != n or any(type(a) is not bool for a in parameters.availability):
        raise ValueError('Disponibilidade CHP incompatível com horizonte')
    if parameters.fuel_limit_kwh_lhv is not None and (
        not isfinite(float(parameters.fuel_limit_kwh_lhv)) or parameters.fuel_limit_kwh_lhv < 0
    ):
        raise ValueError('Limite de combustível CHP inválido')
    model.chp_generation = p.Var(model.T, domain=p.NonNegativeReals)
    model.chp_on = p.Var(model.T, domain=p.Binary)
    model.chp_fuel = p.Var(model.T, domain=p.NonNegativeReals)
    model.chp_capacity = p.Constraint(model.T, rule=lambda m,t:
        m.chp_generation[t] <= capacity_kw * m.chp_on[t])
    model.chp_availability = p.Constraint(model.T, rule=lambda m,t:
        m.chp_on[t] <= int(parameters.availability[t]))
    model.chp_minimum = p.Constraint(model.T, rule=lambda m,t:
        m.chp_generation[t] >= capacity_kw * parameters.minimum_load_fraction * m.chp_on[t])
    model.chp_fuel_link = p.Constraint(model.T, rule=lambda m,t:
        m.chp_fuel[t] * parameters.electric_efficiency == dt_hours * m.chp_generation[t])
    if parameters.fuel_limit_kwh_lhv is not None:
        model.chp_fuel_budget = p.Constraint(expr=sum(model.chp_fuel[t] for t in model.T)
                                             <= parameters.fuel_limit_kwh_lhv)
    # Reutiliza a equação de balanço existente, sem duplicar carga BEV.
    for t in model.T:
        model.balance[t].set_value(model.balance[t].body + model.chp_generation[t] == 0)
    original_objective = model.obj.expr
    model.obj.set_value(original_objective + sum(
        parameters.fuel_brl_per_kwh_lhv * model.chp_fuel[t] +
        parameters.variable_om_brl_per_kwh_e * dt_hours * model.chp_generation[t]
        for t in model.T))
    model._rev021_chp = {'capacity_kw':capacity_kw, 'parameters':parameters,
                        'dt_hours':dt_hours, 'classification':'SYNTHETIC_M5_NOT_D28_RESULT'}
    return model


def solve_chp_operational(model, solver='appsi_highs'):
    """Resolve modelo acoplado; não carrega variáveis de candidatos inviáveis."""
    import pyomo.environ as p
    if not hasattr(model, '_rev021_chp'):
        raise ValueError('Modelo não possui CHP anexado')
    opt = p.SolverFactory(solver)
    if not opt.available(False):
        raise RuntimeError(f'Solver indisponível: {solver}')
    try:
        result = opt.solve(model, load_solutions=False)
    except RuntimeError as exc:
        if 'A feasible solution was not found' in str(exc):
            return {'status':'INFEASIBLE_OR_NOT_OPTIMAL', 'termination':'NO_FEASIBLE_SOLUTION_REPORTED'}
        raise
    termination = result.solver.termination_condition
    if termination != p.TerminationCondition.optimal:
        return {'status':'INFEASIBLE_OR_NOT_OPTIMAL', 'termination':str(termination)}
    model.solutions.load_from(result)
    params = model._rev021_chp['parameters']
    generation = [float(p.value(model.chp_generation[t])) for t in model.T]
    fuel = [float(p.value(model.chp_fuel[t])) for t in model.T]
    grid = [float(p.value(model.grid[t])) for t in model.T]
    return {
        'status':'PASS_SYNTHETIC_OPERATIONAL_CHP',
        'f2_kw':max(grid), 'grid_kw':grid,
        'chp_generation_kw':generation,
        'chp_fuel_kwh_lhv':fuel,
        'chp_recovered_heat_kwh':[
            v * params.heat_recovery_fraction_lhv for v in fuel],
        'chp_fuel_cost_brl':sum(fuel)*params.fuel_brl_per_kwh_lhv,
        'chp_variable_om_brl':sum(generation)*model._rev021_chp['dt_hours']*params.variable_om_brl_per_kwh_e,
        'objective_brl':float(p.value(model.obj)),
        'classification':'SYNTHETIC_M5_NOT_D28_RESULT'}
