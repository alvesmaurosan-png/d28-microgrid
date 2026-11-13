#!/usr/bin/env python3
"""REV16.1.3g: diagnostico isolado do HiGHS, sem alterar arquivos de producao.

Executar na raiz do repositorio: python auditar_d28_rev16_1_3g.py --epsilon 2400
A instrumentacao intercepta somente a instancia Highs criada por solve_economic.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def number(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError, OverflowError):
        return None


def as_json(v):
    if v is None or isinstance(v, (bool, str, int)):
        return v
    if isinstance(v, float):
        return number(v)
    return str(v)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--epsilon', type=float, choices=[2300.0, 2400.0], default=2400.0)
    ap.add_argument('--time-limit', type=float, default=None,
                    help='Opcional: limite em segundos; se omitido, mantem padrao do solver')
    args = ap.parse_args()
    if args.time_limit is not None and (not math.isfinite(args.time_limit) or args.time_limit <= 0):
        ap.error('--time-limit deve ser positivo e finito')

    from pyomo.contrib.appsi import solvers as appsi_solvers
    import pyomo
    import highspy
    import rodar_d28_rev16_1 as base

    original_highs = appsi_solvers.Highs
    captured = {'solver_created': False, 'solve_called': False}

    class InstrumentedHighs(original_highs):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            captured['solver_created'] = True
            if args.time_limit is not None:
                self.config.time_limit = args.time_limit

        def solve(self, model, *a, **kw):
            captured['solve_called'] = True
            import pyomo.environ as p
            from pyomo.core.base.var import Var
            from pyomo.core.base.objective import Objective
            from pyomo.core.base.constraint import Constraint
            captured['model_structure'] = {
                'variables': sum(1 for _ in model.component_data_objects(Var, active=True, descend_into=True)),
                'integer_variables': sum(1 for v in model.component_data_objects(Var, active=True, descend_into=True) if v.is_integer()),
                'binary_variables': sum(1 for v in model.component_data_objects(Var, active=True, descend_into=True) if v.is_binary()),
                'constraints': sum(1 for _ in model.component_data_objects(Constraint, active=True, descend_into=True)),
                'active_objectives': sum(1 for _ in model.component_data_objects(Objective, active=True, descend_into=True)),
            }
            captured['appsi_config'] = {
                'time_limit': as_json(self.config.time_limit),
                'mip_gap': as_json(self.config.mip_gap),
                'load_solution': as_json(self.config.load_solution),
            }
            started = time.perf_counter()
            try:
                res = super().solve(model, *a, **kw)
                captured['elapsed_seconds'] = time.perf_counter() - started
                captured['termination_condition'] = str(res.termination_condition)
                captured['best_feasible_objective'] = number(getattr(res, 'best_feasible_objective', None))
                captured['best_objective_bound'] = number(getattr(res, 'best_objective_bound', None))
                for attr in ('wallclock_time', 'solver_message'):
                    if hasattr(res, attr):
                        captured[attr] = as_json(getattr(res, attr))
                backend = getattr(self, '_solver_model', None)
                if backend is not None:
                    try:
                        info = backend.getInfo()
                        fields = ('mip_gap', 'mip_node_count', 'mip_dual_bound',
                                  'objective_function_value', 'primal_solution_status',
                                  'dual_solution_status', 'simplex_iteration_count',
                                  'ipm_iteration_count', 'max_primal_infeasibility')
                        captured['highs_info'] = {k: as_json(getattr(info, k, None)) for k in fields}
                        captured['highs_model_status'] = str(backend.getModelStatus())
                    except Exception as e:
                        captured['highs_info_error'] = repr(e)
                return res
            except Exception as e:
                captured['elapsed_seconds'] = time.perf_counter() - started
                captured['solve_exception'] = {'type': type(e).__name__, 'message': str(e)}
                raise

    appsi_solvers.Highs = InstrumentedHighs
    result = None
    error = None
    started_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        x, series_path, start = base.inputs()
        cfg_path = ROOT / 'config/economics/r0_f1_exploratory_2026.json'
        cfg = base.Economics.from_json(cfg_path)
        design = {'pv_kw': 1908.225, 'bess_kwh': 15000.0, 'pcs_kw': 5500.0}
        prices = base.EnergyPrices(grid_brl_kwh=(float(cfg.energy_tariff_brl_per_kwh),) * len(x.load_kw))
        result = base.solve_economic('R0', design, x, prices,
            epsilon_kw=args.epsilon, solver_name='appsi_highs',
            months=x.months, demand_tariff_brl_kw_month=cfg.demand_tariff_brl_per_kw_month)
        captured['inputs'] = {'n_intervals': len(x.load_kw), 'dt_hours': x.dt_hours,
                              'series_path': str(series_path.relative_to(ROOT)) if series_path.is_relative_to(ROOT) else str(series_path),
                              'series_sha256': sha(series_path), 'year': start.year,
                              'design': design, 'economics_sha256': sha(cfg_path),
                              'demand_tariff_brl_kw_month': cfg.demand_tariff_brl_per_kw_month,
                              'grid_energy_tariff_brl_kwh': cfg.energy_tariff_brl_per_kwh}
    except Exception as e:
        error = {'type': type(e).__name__, 'message': str(e)}
    finally:
        appsi_solvers.Highs = original_highs

    g1_path = ROOT / 'results/D28_REV16_1_3c_G1_CONSOLIDADO.json'
    g2_path = ROOT / 'results/D28_REV16_1_3e_G2_AUDITORIA.json'
    reference = None
    if g1_path.is_file():
        for row in read_json(g1_path).get('rows', []):
            if number(row.get('epsilon_kw')) == args.epsilon:
                reference = {'epsilon_kw': args.epsilon,
                             'annual_milp_objective_brl': number(row.get('milp_objective_brl')),
                             'f2_kw': number(row.get('f2_kw'))}
                break
    actual = None
    if isinstance(result, dict):
        actual = {'status': result.get('status'), 'reason': result.get('reason'),
                  'cost_brl': number(result.get('cost_brl')),
                  'f2_kw': number(result.get('pilot_f2_kw')),
                  'max_constraint_violation_native': number(result.get('max_constraint_violation_native')),
                  'checks': result.get('checks'), 'solver_termination': result.get('solver_termination')}
    comparison = {}
    if actual and reference:
        if actual['cost_brl'] is not None and reference['annual_milp_objective_brl'] is not None:
            comparison['delta_annual_cost_brl'] = actual['cost_brl'] - reference['annual_milp_objective_brl']
        if actual['f2_kw'] is not None and reference['f2_kw'] is not None:
            comparison['delta_f2_kw'] = actual['f2_kw'] - reference['f2_kw']
    lo = captured.get('best_objective_bound')
    hi = captured.get('best_feasible_objective')
    if lo is not None and hi is not None and math.isfinite(lo) and math.isfinite(hi):
        captured['absolute_gap_from_bounds'] = max(0.0, hi - lo)
        captured['relative_gap_from_bounds'] = max(0.0, hi - lo) / max(1.0, abs(hi))

    output = {
        'revision': 'REV16.1.3g', 'scope': 'DIAGNOSTIC_R0_E100_FIXED_DESIGN',
        'classification': 'DIAGNOSTIC_NOT_HOMOLOGATION', 'timestamp_utc': started_utc,
        'epsilon_kw': args.epsilon, 'time_limit_seconds': args.time_limit,
        'versions': {'python': platform.python_version(), 'pyomo': getattr(pyomo, '__version__', None),
                     'highspy': getattr(highspy, '__version__', 'UNKNOWN')},
        'source_hashes': {
            'economic_dispatch_f1f2.py': sha(ROOT / 'src/d28/optimization/economic_dispatch_f1f2.py'),
            'biobjective_milp_connector.py': sha(ROOT / 'src/d28/optimization/biobjective_milp_connector.py'),
            'rodar_d28_rev16_1.py': sha(ROOT / 'rodar_d28_rev16_1.py'),
            'g1_consolidated': sha(g1_path), 'g2_audit': sha(g2_path),
        },
        'solver': captured, 'actual': actual, 'g1_reference': reference,
        'comparison': comparison, 'error': error,
        'nsga2_authorized': False,
        'limitations': ['Nao substitui os relatórios G1/G2',
                        'Nao certifica monotonicidade entre dois epsilons sem comparacao de execucoes',
                        'Termino optimal sem bounds/gap e verificacao numerica nao basta para certificacao independente']
    }
    out_dir = ROOT / 'results'
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f'D28_REV16_1_3g_DIAGNOSTICO_EPS_{int(args.epsilon)}.json'
    if out_path.exists():
        print('ERRO: relatorio ja existe; preservado sem sobrescrita:', out_path)
        return 4
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print('REV16.1.3g | DIAGNOSTICO HiGHS')
    print('EPSILON:', args.epsilon)
    print('STATUS:', actual.get('status') if actual else 'ERROR')
    print('TERMINATION:', captured.get('termination_condition', 'UNAVAILABLE'))
    print('MODEL_STRUCTURE:', captured.get('model_structure', 'UNAVAILABLE'))
    print('BEST_FEASIBLE_OBJECTIVE:', captured.get('best_feasible_objective'))
    print('BEST_OBJECTIVE_BOUND:', captured.get('best_objective_bound'))
    print('HIGHS_INFO:', captured.get('highs_info', 'UNAVAILABLE'))
    print('COST_DELTA_VS_G1:', comparison.get('delta_annual_cost_brl'))
    print('NSGA2_AUTHORIZED: False')
    print('REPORT:', out_path)
    if error:
        print('ERROR:', error)
    return 0 if actual and actual.get('status') == 'PASS' else 2

if __name__ == '__main__':
    raise SystemExit(main())
