"""REV02.1 M1-M3: despacho cronologico individual BEV, sintético e isolado.

Nao altera dispatch.py, integration.py ou contratos existentes.
As entradas de carga representam somente cargas AC nao atribuídas aos BEVs.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Tuple


@dataclass(frozen=True)
class Bus:
    bus_id: str
    initial_kwh: float
    capacity_kwh: float
    minimum_kwh: float
    maximum_charge_kw: float
    # energia consumida no intervalo; nao pode carregar enquanto em servico
    traction_kwh: Tuple[float, ...]
    available: Tuple[bool, ...]
    terminal_minimum_kwh: float
    charging_efficiency: float = 0.92


@dataclass(frozen=True)
class Cabinet:
    cabinet_id: str
    shared_limit_kw: float
    connectors: int
    eligible_bus_ids: Tuple[str, ...]


def build_operational_milp(*, buses, cabinets, base_load_kw, pv_pu,
                           dt_hours, pcc_cap_kw, pv_kw=0.,
                           bess_kwh=0., pcs_kw=0., tariff_brl_kwh=None,
                           eta_bess_charge=0.922, eta_bess_discharge=0.922):
    """MILP de operacao, sem agregacao de demanda individual e sem CHP.

    Vinculo bus-cabinet por intervalo, maximo de conectores, potencia
    compartilhada, energia de tracao e estado de carga de cada BEV.
    """
    import pyomo.environ as p
    buses, cabinets = tuple(buses), tuple(cabinets)
    n = len(base_load_kw)
    if not buses or not cabinets or not n or len(pv_pu) != n:
        raise ValueError('Entradas incompletas')
    if tariff_brl_kwh is not None and len(tariff_brl_kwh) != n:
        raise ValueError('Tarifa temporal inconsistente')
    if len({b.bus_id for b in buses}) != len(buses) or len({c.cabinet_id for c in cabinets}) != len(cabinets):
        raise ValueError('IDs duplicados')
    if dt_hours <= 0 or pcc_cap_kw <= 0 or min(pv_kw,bess_kwh,pcs_kw) < 0:
        raise ValueError('Parametros de capacidade invalidos')
    if not (0 < eta_bess_charge <= 1 and 0 < eta_bess_discharge <= 1):
        raise ValueError('Eficiencia BESS invalida')
    if pcs_kw > 0.55*bess_kwh + 1e-8:
        raise ValueError('C-rate BESS provisoria excedida')
    series = list(base_load_kw)+list(pv_pu)+(list(tariff_brl_kwh) if tariff_brl_kwh is not None else [])
    if any(not isfinite(float(x)) or float(x) < 0 for x in series):
        raise ValueError('Serie invalida')
    ids = {b.bus_id for b in buses}
    for b in buses:
        if (len(b.available) != n or len(b.traction_kwh) != n or
            not 0 <= b.minimum_kwh <= b.initial_kwh <= b.capacity_kwh or
            not b.minimum_kwh <= b.terminal_minimum_kwh <= b.capacity_kwh or
            b.maximum_charge_kw <= 0 or not 0 < b.charging_efficiency <= 1 or
            any(not isfinite(float(e)) or e < 0 for e in b.traction_kwh)):
            raise ValueError(f'Contrato individual invalido: {b.bus_id}')
    for c in cabinets:
        if c.shared_limit_kw <= 0 or c.connectors < 1 or not set(c.eligible_bus_ids) <= ids:
            raise ValueError(f'Gabinete invalido: {c.cabinet_id}')
    pairs = tuple((b.bus_id,c.cabinet_id) for b in buses for c in cabinets if b.bus_id in c.eligible_bus_ids)
    if any(not any(pair[0] == b.bus_id for pair in pairs) for b in buses):
        raise ValueError('BEV sem gabinete elegivel')
    bybus = {b.bus_id:b for b in buses}
    bycab = {c.cabinet_id:c for c in cabinets}
    m = p.ConcreteModel()
    m.T = p.RangeSet(0,n-1)
    m.S = p.RangeSet(0,n)
    m.B = p.Set(initialize=list(bybus))
    m.C = p.Set(initialize=list(bycab))
    m.BC = p.Set(dimen=2, initialize=pairs)
    m.grid = p.Var(m.T, domain=p.NonNegativeReals, bounds=(0,pcc_cap_kw))
    m.pv = p.Var(m.T, domain=p.NonNegativeReals)
    m.bess_ch = p.Var(m.T, domain=p.NonNegativeReals)
    m.bess_dis = p.Var(m.T, domain=p.NonNegativeReals)
    m.bess_mode = p.Var(m.T, domain=p.Binary)
    m.bess_soc = p.Var(m.S, bounds=(0.1*bess_kwh,0.9*bess_kwh))
    m.bus_soc = p.Var(m.B,m.S, domain=p.NonNegativeReals)
    m.connect = p.Var(m.BC,m.T, domain=p.Binary)
    m.charge = p.Var(m.BC,m.T, domain=p.NonNegativeReals)
    m.bus_soc_bound = p.Constraint(m.B,m.S,rule=lambda m,b,t: p.inequality(bybus[b].minimum_kwh,m.bus_soc[b,t],bybus[b].capacity_kwh))
    m.bus_initial = p.Constraint(m.B,rule=lambda m,b: m.bus_soc[b,0] == bybus[b].initial_kwh)
    m.bus_terminal = p.Constraint(m.B,rule=lambda m,b: m.bus_soc[b,n] >= bybus[b].terminal_minimum_kwh)
    m.bus_transition = p.Constraint(m.B,m.T,rule=lambda m,b,t:
        m.bus_soc[b,t+1] == m.bus_soc[b,t] + dt_hours*bybus[b].charging_efficiency*
        sum(m.charge[b,c,t] for bb,c in pairs if bb==b) - bybus[b].traction_kwh[t])
    m.availability = p.Constraint(m.BC,m.T,rule=lambda m,b,c,t:
        m.connect[b,c,t] <= int(bybus[b].available[t]))
    m.charge_limit = p.Constraint(m.BC,m.T,rule=lambda m,b,c,t:
        m.charge[b,c,t] <= min(bybus[b].maximum_charge_kw,bycab[c].shared_limit_kw)*m.connect[b,c,t])
    m.single_connection = p.Constraint(m.B,m.T,rule=lambda m,b,t:
        sum(m.connect[b,c,t] for bb,c in pairs if bb==b) <= 1)
    m.connectors = p.Constraint(m.C,m.T,rule=lambda m,c,t:
        sum(m.connect[b,c,t] for b,cc in pairs if cc==c) <= bycab[c].connectors)
    m.cabinet_power = p.Constraint(m.C,m.T,rule=lambda m,c,t:
        sum(m.charge[b,c,t] for b,cc in pairs if cc==c) <= bycab[c].shared_limit_kw)
    m.pv_limit = p.Constraint(m.T,rule=lambda m,t: m.pv[t] <= pv_kw*float(pv_pu[t]))
    m.bess_charge_limit = p.Constraint(m.T,rule=lambda m,t: m.bess_ch[t] <= pcs_kw*m.bess_mode[t])
    m.bess_discharge_limit = p.Constraint(m.T,rule=lambda m,t: m.bess_dis[t] <= pcs_kw*(1-m.bess_mode[t]))
    m.bess_transition = p.Constraint(m.T,rule=lambda m,t:
        m.bess_soc[t+1] == m.bess_soc[t]+dt_hours*(eta_bess_charge*m.bess_ch[t]-m.bess_dis[t]/eta_bess_discharge))
    m.bess_initial = p.Constraint(expr=m.bess_soc[0] == 0.5*bess_kwh)
    m.bess_terminal = p.Constraint(expr=m.bess_soc[n] == m.bess_soc[0])
    m.balance = p.Constraint(m.T,rule=lambda m,t:
        m.grid[t]+m.pv[t]+m.bess_dis[t] == float(base_load_kw[t])+m.bess_ch[t]+
        sum(m.charge[b,c,t] for b,c in pairs))
    tariff = tariff_brl_kwh if tariff_brl_kwh is not None else (1.,)*n
    m.obj = p.Objective(expr=sum(float(tariff[t])*dt_hours*m.grid[t] for t in m.T))
    m._rev021 = {'classification':'SYNTHETIC_OPERATIONAL_M1_M3_NOT_D28_RESULT',
                  'bus_count':len(buses),'cabinet_count':len(cabinets),'periods':n}
    return m


def solve_operational_milp(model, solver='appsi_highs'):
    import pyomo.environ as p
    opt = p.SolverFactory(solver)
    if not opt.available(False):
        raise RuntimeError(f'Solver indisponivel: {solver}')
    try:
        result = opt.solve(model)
    except RuntimeError as exc:
        if "A feasible solution was not found" in str(exc):
            return {"status":"INFEASIBLE_OR_NOT_OPTIMAL", "termination":"NO_FEASIBLE_SOLUTION_REPORTED"}
        raise
    termination = result.solver.termination_condition
    if termination != p.TerminationCondition.optimal:
        return {'status':'INFEASIBLE_OR_NOT_OPTIMAL','termination':str(termination)}
    return {'status':'PASS_SYNTHETIC_OPERATIONAL',
            'f2_kw':max(float(p.value(model.grid[t])) for t in model.T),
            'objective_brl':float(p.value(model.obj)),
            'grid_kw':[float(p.value(model.grid[t])) for t in model.T],
            'charging_kw':{b:[sum(float(p.value(model.charge[bb,c,t])) for bb,c in model.BC if bb==b)
                               for t in model.T] for b in model.B},
            'bus_terminal_kwh':{b:float(p.value(model.bus_soc[b,len(model.T)])) for b in model.B},
            'classification':'SYNTHETIC_OPERATIONAL_M1_M3_NOT_D28_RESULT'}
