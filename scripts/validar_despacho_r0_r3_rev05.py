"""Gate numérico físico R0–R3, sintético, sem F1/F3 ou liberação de M6.
Executar da raiz: python scripts/validar_despacho_r0_r3_rev05.py
"""
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import pyomo.environ as p
from d28.dispatch.milp import build_r0_milp
from d28.dispatch.r1 import build_r1_milp
from d28.dispatch.r2_r3 import build_r2_milp, build_r3_milp

DT = 0.25
LOAD = [100.0, 150.0, 120.0, 80.0]
SOLAR = [0.0, 0.3, 0.5, 0.1]
COMMON = dict(load_kw=LOAD, pv_pu=SOLAR, pv_capacity_kw=100.0,
              bess_capacity_kwh=100.0, pcs_power_kw=40.0,
              pcc_cap_kw=2500.0, dt_hours=DT, terminal_policy='cyclic')
CHP = dict(chp_capacity_kw=60.0, electrical_efficiency=0.30,
           fuel_lhv_kwh_per_nm3=6.0, availability=[1, 1, 1, 1])


def build(route):
    if route == 'R0':
        return build_r0_milp(**COMMON)
    if route == 'R1':
        return build_r1_milp(**COMMON, **CHP)
    if route == 'R2':
        return build_r2_milp(**COMMON, **CHP, production_nm3=[5.0] * 4,
                             gasometer_capacity_nm3=50.0, initial_gas_nm3=20.0)
    if route == 'R3':
        return build_r3_milp(**COMMON, **CHP, cgob_coverage_nm3=1.0)
    raise ValueError(route)


def run():
    solver = p.SolverFactory('appsi_highs')
    if not solver.available(exception_flag=False):
        raise RuntimeError('HiGHS indisponível')
    results = {}
    for route in ('R0', 'R1', 'R2', 'R3'):
        m = build(route)
        solution = solver.solve(m, load_solutions=False)
        term = solution.solver.termination_condition
        if term != p.TerminationCondition.optimal:
            raise RuntimeError(f'{route}: MILP não ótimo ({term})')
        m.solutions.load_from(solution)
        balances = []
        grid = []
        fuel = []
        for t in m.T:
            g = float(p.value(m.grid[t])); grid.append(g)
            chp = float(p.value(m.chp.power_gross_kw[t])) if route != 'R0' else 0.0
            aux = float(p.value(m.auxiliary_load_kw[t])) if route == 'R2' else 0.0
            left = g + float(p.value(m.pv[t])) + float(p.value(m.bess_discharge[t])) + chp
            right = float(p.value(m.load_kw[t])) + float(p.value(m.bess_charge[t])) + aux
            balances.append(abs(left - right))
            if route != 'R0':
                fuel.append(float(p.value(m.chp.fuel_nm3[t])))
        residual = max(balances)
        if not math.isfinite(residual) or residual > 1e-6:
            raise AssertionError(f'{route}: balanço elétrico residual {residual}')
        if route == 'R2':
            gas_residual = max(abs(float(p.value(m.gas_transition[t].body))) for t in m.T)
            if gas_residual > 1e-6:
                raise AssertionError(f'R2: balanço de gás residual {gas_residual}')
        else:
            gas_residual = None
        results[route] = dict(status='OPTIMAL', grid_kwh=sum(grid)*DT,
                              peak_pcc_kw=max(grid), electric_balance_max_kw=residual,
                              chp_fuel_nm3=sum(fuel), gas_balance_max_nm3=gas_residual,
                              scope='SYNTHETIC_PHYSICAL_SMOKE_NOT_ANNUAL')
    output = ROOT / 'reports' / 'REV05_GATE_FISICO_R0_R3.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({'scientific_nsga2_released': False,
                                  'f1_f3_calculated': False,
                                  'annual_contract_approved': False,
                                  'results': results}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print('Relatório:', output)


if __name__ == '__main__':
    run()
