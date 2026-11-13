"""R0 experimental multidia: triagem fisica + MILP lexicografico + NSGA-II.

Execucao no repositorio: python -m d28.optimization.r0_nsga2_multiday
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize

from d28.optimization.r0_nsga2_integrated import solve_lex

DAYS = (149, 183, 216, 279, 359)
DT = 0.25
PCC = 2500.0


def get_result_peak(result):
    if result is None:
        return None
    if not isinstance(result, dict):
        raise TypeError(f"Retorno inesperado de solve_lex: {type(result).__name__}")
    value = result.get('F2_kw', result.get('grid_peak_kw'))
    if value is None or not np.isfinite(float(value)):
        raise ValueError('Pico de rede ausente ou nao finito')
    return float(value)


def load_inputs(root):
    source = root / 'data/processed/milp_inputs/R0_inputs_E100_15min.csv'
    frame = pd.read_csv(source)
    if len(frame) != 35040:
        raise ValueError(f'Esperados 35040 intervalos; recebidos {len(frame)}')
    loads = frame['load_charging_ac_kw'].to_numpy(dtype=float).reshape(365, 96)
    solar = frame['pv_kw_per_kwp'].to_numpy(dtype=float).reshape(365, 96)
    if not np.isfinite(loads).all() or not np.isfinite(solar).all() or (loads < 0).any() or (solar < 0).any():
        raise ValueError('Serie de carga/PV contem valores invalidos')
    return loads, solar


def evaluate_design(x, loads, solar, days, counters):
    pv, bess, pcs = map(float, x)
    # Condicao necessaria de potencia: mesmo com BESS sempre descarregando a PCS,
    # PV totalmente disponivel e rede no limite, nao pode haver deficit.
    worst = max(float(np.max(loads[d] - pv * solar[d] - pcs - PCC)) for d in days)
    if worst > 1e-6:
        counters['screen_rejected'] += 1
        return {'feasible': False, 'violation_kw': worst, 'reason': 'POWER_SCREEN', 'peaks': {}}
    peaks = {}
    for d in days:
        counters['milp_calls'] += 1
        result = solve_lex(loads[d], solar[d], pv, bess, pcs, pcc_kw=PCC)
        peak = get_result_peak(result)
        if peak is None:
            counters['milp_nonoptimal'] += 1
            return {'feasible': False, 'violation_kw': 0.0, 'reason': f'MILP_NO_OPTIMUM_DAY_{d}', 'peaks': peaks}
        if peak > PCC + 1e-5:
            raise RuntimeError(f'Violacao PCC: dia {d}, pico {peak}')
        peaks[str(d)] = peak
    counters['feasible'] += 1
    return {'feasible': True, 'violation_kw': 0.0, 'reason': 'ALL_DAYS_OPTIMAL', 'peaks': peaks, 'max_peak_kw': max(peaks.values())}


class MultidayProblem(ElementwiseProblem):
    def __init__(self, loads, solar, days, bounds, weights):
        super().__init__(n_var=3, n_obj=2, n_ieq_constr=1,
                         xl=np.array([bounds[k][0] for k in ('pv','bess','pcs')], dtype=float),
                         xu=np.array([bounds[k][1] for k in ('pv','bess','pcs')], dtype=float))
        self.loads, self.solar, self.days = loads, solar, days
        self.design_bounds, self.weights = bounds, weights
        self.counters = {'evaluations': 0, 'screen_rejected': 0, 'milp_calls': 0, 'milp_nonoptimal': 0, 'feasible': 0}
        self.cache = {}

    def _evaluate(self, x, out, *args, **kwargs):
        self.counters['evaluations'] += 1
        key = tuple(round(float(v), 8) for v in x)
        if key not in self.cache:
            self.cache[key] = evaluate_design(x, self.loads, self.solar, self.days, self.counters)
        r = self.cache[key]
        # Indice experimental normalizado, nao e custo F1.
        idx = sum(self.weights[k] * float(x[j]) / self.design_bounds[k][1] for j, k in enumerate(('pv','bess','pcs')))
        if r['feasible']:
            out['F'] = [idx, r['max_peak_kw']]
            out['G'] = [-1.0]
        else:
            # A restricao positiva impede que pontos inviaveis integrem a fronteira.
            # Penalidade 1 e usada quando a inviabilidade e energetica/MILP.
            out['F'] = [idx, PCC + max(0.0, r['violation_kw'])]
            out['G'] = [1.0 + max(0.0, r['violation_kw']) / PCC]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--population', type=int, default=24)
    parser.add_argument('--generations', type=int, default=8)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--pv-max', type=float, default=10000)
    parser.add_argument('--bess-max', type=float, default=40000)
    parser.add_argument('--pcs-max', type=float, default=10000)
    parser.add_argument('--out', default='results/r0_nsga2_multiday')
    args = parser.parse_args()
    if args.population < 4 or args.generations < 1:
        parser.error('population >= 4 e generations >= 1 sao obrigatorios')
    root = Path.cwd()
    loads, solar = load_inputs(root)
    bounds = {'pv': (0.0, args.pv_max), 'bess': (0.0, args.bess_max), 'pcs': (0.0, args.pcs_max)}
    if any(hi <= lo for lo, hi in bounds.values()):
        parser.error('Limites superiores devem ser positivos')
    # Pesos iguais explicitamente provisórios. NAO equivalem ao indice do smoke anterior.
    weights = {'pv': 1.0, 'bess': 1.0, 'pcs': 1.0}
    problem = MultidayProblem(loads, solar, DAYS, bounds, weights)
    result = minimize(problem, NSGA2(pop_size=args.population),
                      termination=('n_gen', args.generations), seed=args.seed,
                      verbose=True)
    outdir = root / args.out
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    if result.X is not None and result.F is not None:
        xs = np.atleast_2d(result.X)
        for x in xs:
            key = tuple(round(float(v), 8) for v in x)
            r = problem.cache.get(key)
            if r is None or not r['feasible']:
                continue
            row = {'pv_kwp': float(x[0]), 'bess_kwh': float(x[1]), 'pcs_kw': float(x[2]),
                   'size_index_NOT_F1': sum(float(x[j]) / bounds[k][1] for j,k in enumerate(('pv','bess','pcs'))),
                   'F2_multiday_max_kw': r['max_peak_kw'], 'feasible_all_days': True}
            for day in DAYS:
                row[f'grid_peak_day_{day}_kw'] = r['peaks'][str(day)]
            rows.append(row)
    csv_path = outdir / 'pareto_multiday.csv'
    columns = ['pv_kwp', 'bess_kwh', 'pcs_kw', 'size_index_NOT_F1', 'F2_multiday_max_kw', 'feasible_all_days'] + [f'grid_peak_day_{d}_kw' for d in DAYS]
    pd.DataFrame(rows, columns=columns).to_csv(csv_path, index=False)
    summary = {'status': 'MULTIDAY_EXPERIMENTAL_NOT_SCIENTIFIC', 'scenario': 'E100',
               'days': list(DAYS), 'pcc_kw': PCC, 'dt_hours': DT,
               'terminal_soc_policy': 'inherited_from_solve_lex_per_day',
               'population': args.population, 'generations': args.generations, 'seed': args.seed,
               'bounds': bounds, 'experimental_index_weights': weights,
               'counters': problem.counters, 'nondominated_feasible': len(rows),
               'F1': 'NOT_COMPUTED', 'F3': 'NOT_COMPUTED',
               'annual_feasibility': 'NOT_VALIDATED', 'result_csv': str(csv_path)}
    (outdir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print('MULTIDAY_SUMMARY')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

