"""REV03: quatro MILPs sintéticos de 15 min, sem GA e sem contabilidade anual."""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pyomo.environ as p
from d28.optimization.biobjective_milp_connector import (
    ConnectorInputs, build_route_milp, solve_peak_then_energy,
)

LOAD = (100.0, 150.0, 120.0, 80.0)
PV_PU = (0.0, 0.3, 0.5, 0.1)
DESIGN = {'pv_kw': 100.0, 'bess_kwh': 500.0, 'pcs_kw': 100.0}
CHP = {'chp_capacity_kw': 80.0, 'electrical_efficiency': 0.35,
       'fuel_lhv_kwh_per_nm3': 10.0, 'availability': (1, 1, 1, 1)}
OPTIONS = {
    'R0': {},
    'R1': dict(CHP),
    'R2': {**CHP, 'production_nm3': (10.0,)*4,
           'gasometer_capacity_nm3': 200.0, 'initial_gas_nm3': 100.0,
           'auxiliary_kw': (2.0,)*4, 'terminal_gas_policy': 'cyclic'},
    'R3': {**CHP, 'cgob_coverage_nm3': 0.0},
}


def constraint_residuals(model):
    """Máxima violação das desigualdades/igualdades ativas, em unidades próprias."""
    maximum = 0.0
    worst = None
    checked = 0
    for c in model.component_data_objects(p.Constraint, active=True, descend_into=True):
        body = p.value(c.body, exception=False)
        if body is None or not math.isfinite(float(body)):
            raise RuntimeError(f'CONSTRAINT_VALUE_UNAVAILABLE: {c.name}')
        violation = 0.0
        if c.has_lb():
            violation = max(violation, float(p.value(c.lower)) - float(body))
        if c.has_ub():
            violation = max(violation, float(body) - float(p.value(c.upper)))
        violation = max(0.0, violation)
        checked += 1
        if violation > maximum:
            maximum, worst = violation, c.name
    return {'constraints_checked': checked, 'max_violation_native_units': maximum,
            'worst_constraint': worst}


def run_one(route, tol):
    inputs = ConnectorInputs(load_kw=LOAD, pv_pu=PV_PU, dt_hours=0.25,
                             pcc_cap_kw=2500.0, terminal_policy='cyclic',
                             route_options=OPTIONS[route])
    record = {'route': route, 'candidate': DESIGN, 'intervals': 4,
              'dt_hours': 0.25, 'annual_f1_brl_per_pkm': None,
              'f3_excluded': True, 'nsga2_executed': False,
              'synthetic_test_only': True}
    try:
        model = build_route_milp(route, DESIGN, inputs)
        result = solve_peak_then_energy(model, dt_hours=0.25,
                                        solver_name='appsi_highs')
        record['solver_audit'] = result['audit']
        if not result['optimal']:
            record.update(status='FAILED', reason='MILP_NOT_OPTIMAL')
            return record
        grid = [float(x) for x in result['grid_kw']]
        record['grid_kw'] = grid
        record['pilot_f2_peak_kw'] = max(grid)
        record['pilot_grid_energy_kwh'] = sum(grid)*0.25
        record['constraints'] = constraint_residuals(model)
        record['pcc_cap_kw'] = inputs.pcc_cap_kw
        record['pcc_margin_kw'] = inputs.pcc_cap_kw-max(grid)
        record['balance_max_abs_kw'] = max(
            abs(float(p.value(model.balance[t].body))) for t in model.T
        )
        if hasattr(model, 'gas_stock'):
            record['gas_stock_nm3'] = [float(p.value(model.gas_stock[t]))
                                       for t in range(len(LOAD)+1)]
        if hasattr(model, 'chp'):
            record['chp_gross_kw'] = [float(p.value(model.chp.power_gross_kw[t]))
                                      for t in model.T]
        valid = (all(math.isfinite(x) and -tol <= x <= inputs.pcc_cap_kw+tol for x in grid)
                 and record['constraints']['max_violation_native_units'] <= tol
                 and record['balance_max_abs_kw'] <= tol)
        record.update(status='PASS' if valid else 'FAILED',
                      reason='PHYSICAL_CHECKS_OK' if valid else 'PHYSICAL_RESIDUAL')
    except Exception as exc:
        record.update(status='ERROR', reason=f'{type(exc).__name__}: {exc}')
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='results/rev03_piloto_fisico_r0_r3.json')
    ap.add_argument('--tolerance', type=float, default=1e-5)
    args = ap.parse_args()
    if not 0 < args.tolerance <= 1e-2:
        ap.error('tolerance must be in (0, 1e-2]')
    report = {'protocol': 'D28_REV03_PHYSICAL_PILOT',
              'generated_utc': datetime.now(timezone.utc).isoformat(),
              'dispatch_policy': 'MIN_PEAK_THEN_MIN_GRID_ENERGY',
              'dispatch_is_f1_optimal': False,
              'annual_accounting_performed': False,
              'population_executed': False,
              'input_origin': 'SYNTHETIC_SMOKE_TEST_NOT_HOMOLOGATED',
              'tolerance': args.tolerance,
              'results': [run_one(route, args.tolerance) for route in ('R0','R1','R2','R3')]}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    for item in report['results']:
        print(f"{item['route']}: {item['status']} | {item['reason']} | F2_piloto={item.get('pilot_f2_peak_kw', 'N/A')} kW")
    print(f'Auditoria: {path}')
    return 0 if all(r['status']=='PASS' for r in report['results']) else 1

if __name__ == '__main__':
    raise SystemExit(main())
