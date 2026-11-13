"""REV16.1.4c: busca NSGA-II + MILP R0/E100, estritamente exploratoria.

Reutiliza o executor REV16.1.4 sem alterar suas verificacoes ou seus arquivos.
Um ponto so entra na fronteira de resultados aceitos se o executor o aprovar.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

BOUNDS = ((0., 1908.225), (0., 30000.), (0., 16500.))
NAMES = ('pv_kw', 'bess_kwh', 'pcs_kw')


def write_json_atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temp.replace(path)


F1_TOL = 1e-12
F2_TOL_KW = 1e-8
INDETERMINATE_REASONS = {'EXTERNAL_TIMEOUT_NOT_PROOF_OF_INFEASIBILITY',
                         'INTERNAL_TIME_LIMIT_NOT_PROOF_OF_INFEASIBILITY',
                         'MILP_UNKNOWN_NOT_PROOF_OF_INFEASIBILITY', 'EXECUTOR_ERROR'}


class IndeterminateEvaluation(RuntimeError):
    """Interrompe a evolucao: sem objetivos certificados, nao penalizar como inviavel."""


def is_indeterminate(rec):
    return rec.get('reason') in INDETERMINATE_REASONS or rec.get('solver_state') in ('TIME_LIMIT', 'UNKNOWN', 'ERROR', 'AUDIT_FAILED')


def non_dominated(rows):
    accepted = [r for r in rows if r.get('accepted')]
    result = []
    for a in accepted:
        fa, pa = a['f1_brl_per_pkm'], a['f2_kw']
        if not any(b is not a and
                   b['f1_brl_per_pkm'] <= fa + F1_TOL and
                   b['f2_kw'] <= pa + F2_TOL_KW and
                   (b['f1_brl_per_pkm'] < fa - F1_TOL or
                    b['f2_kw'] < pa - F2_TOL_KW)
                   for b in accepted):
            result.append(a)
    return sorted(result, key=lambda r: (r['f2_kw'], r['f1_brl_per_pkm']))


def cache_reusable(rec):
    """Nao reutiliza automaticamente resultados sem conclusao certificada."""
    return not is_indeterminate(rec)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', default='data/processed/milp_inputs/R0_inputs_E100_15min.csv')
    parser.add_argument('--executor', default='rev16_1_4/executar_r0_e100_rev16_1_4.py')
    parser.add_argument('--output-dir', default='results/REV16_1_4c_NSGA2_R0_E100')
    parser.add_argument('--population', type=int, default=4)
    parser.add_argument('--generations', type=int, default=2)
    parser.add_argument('--epsilon', type=float, default=2500.)
    parser.add_argument('--seed', type=int, default=14)
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    parser.add_argument('--solver-time-limit-seconds', type=float, default=1500.)
    parser.add_argument('--allow-stale-evidence', action='store_true')
    args = parser.parse_args()
    if args.population < 4 or args.generations < 1 or args.timeout_seconds < 1:
        parser.error('population >= 4, generations >= 1, timeout-seconds >= 1')
    if not (math.isfinite(args.solver_time_limit_seconds) and 0 < args.solver_time_limit_seconds < args.timeout_seconds):
        parser.error('solver-time-limit-seconds deve ser positivo e menor que timeout-seconds')
    if not (0 <= args.epsilon <= 2500):
        parser.error('epsilon deve estar entre 0 e 2500 kW')
    try:
        import numpy as np
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.problem import ElementwiseProblem
        from pymoo.optimize import minimize
    except ImportError as exc:
        parser.error(f'Dependencia ausente: {exc}. Instale pymoo no ambiente atual.')

    root = Path.cwd()
    csv_path = (root / args.csv).resolve()
    exe_path = (root / args.executor).resolve()
    if not csv_path.is_file() or not exe_path.is_file():
        parser.error('CSV E100 ou executor REV16.1.4 nao encontrado')
    out = (root / args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    csv_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    exe_hash = hashlib.sha256(exe_path.read_bytes()).hexdigest()
    # Hash de configuracoes para invalidar cache quando premissas mudarem.
    paths = ['config/contrato_sintetico_rev11.json', 'config/annual_f1_f2_evidence.json',
             'config/economics/r0_f1_exploratory_2026.json',
             'config/tariffs/rev07_scenarios_exploratory.json',
             'src/d28/optimization/economic_dispatch_f1f2.py', 'src/d28/economics/f1.py']
    config_hashes = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    identity = dict(csv_sha256=csv_hash, executor_sha256=exe_hash,
                    configs=config_hashes, epsilon_kw=args.epsilon,
                    allow_stale_evidence=args.allow_stale_evidence,
                    solver_time_limit_seconds=args.solver_time_limit_seconds,
                    timeout_seconds=args.timeout_seconds)
    identity_hash = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    cache_path = out / f'cache_{identity_hash}.json'
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    cache = {k:v for k,v in cache.items() if cache_reusable(v)}
    state = {'revision': 'REV16.1.4c', 'method': 'NSGA-II + ANNUAL_MILP',
             'scope': 'R0_E100_SYNTHETIC_EXPLORATORY_ONLY', 'scientific_homologation': False,
             'identity': identity, 'population': args.population, 'generations': args.generations,
             'seed': args.seed, 'evaluations': [], 'nondominated_accepted': [],
             'completed': False, 'run_status': 'RUNNING'}
    # Reaproveita o pre-filtro do executor (import sem executar main).
    import importlib.util
    spec = importlib.util.spec_from_file_location('rev16_1_4_executor', exe_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    loads, solar, _ = module.load_inputs(csv_path, 2025)

    def evaluate_candidate(x):
        d = {name: round(float(value), 4) for name, value in zip(NAMES, x)}
        key = ','.join(f'{d[n]:.4f}' for n in NAMES)
        if key in cache and cache_reusable(cache[key]):
            return cache[key]
        pre = module.analytical_prefilter(d, args.epsilon, loads, solar, 2500.)
        if not pre['passed']:
            rec = {'design': d, 'epsilon_kw': args.epsilon, 'accepted': False,
                   'reason': pre['reason'], 'analytical_prefilter': pre,
                   'solver_status': 'NOT_CALLED_ANALYTICAL_REJECTION'}
        else:
            candidate_path = out / 'candidate_current.json'
            result_path = out / 'result_current.json'
            write_json_atomic(candidate_path, [d])
            result_path.unlink(missing_ok=True)
            cmd = [sys.executable, str(exe_path), '--csv', str(csv_path),
                   '--designs', str(candidate_path), '--epsilons', str(args.epsilon),
                   '--out', str(result_path), '--max-solves', '1',
                   '--solver-time-limit-seconds', str(args.solver_time_limit_seconds)]
            if args.allow_stale_evidence:
                cmd.append('--allow-stale-evidence')
            import time
            start = time.perf_counter()
            try:
                run = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                                     timeout=args.timeout_seconds, check=False)
                if result_path.exists() and run.returncode == 0:
                    report = json.loads(result_path.read_text(encoding='utf-8'))
                    if not report.get('evaluations'):
                        raise ValueError('EMPTY_EXECUTOR_REPORT')
                    rec = report['evaluations'][0]
                    if rec.get('solver_state') == 'TIME_LIMIT':
                        rec['reason'] = 'INTERNAL_TIME_LIMIT_NOT_PROOF_OF_INFEASIBILITY'
                    elif rec.get('solver_state') in ('UNKNOWN', 'ERROR'):
                        rec['reason'] = 'MILP_UNKNOWN_NOT_PROOF_OF_INFEASIBILITY'
                else:
                    rec = {'design': d, 'epsilon_kw': args.epsilon, 'accepted': False,
                           'reason': 'EXECUTOR_ERROR', 'returncode': run.returncode,
                           'stderr_tail': run.stderr[-2000:], 'stdout_tail': run.stdout[-2000:]}
            except (OSError, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
                rec = {'design': d, 'epsilon_kw': args.epsilon, 'accepted': False,
                       'reason': 'EXECUTOR_ERROR', 'error': f'{type(exc).__name__}: {exc}'}
            except subprocess.TimeoutExpired:
                rec = {'design': d, 'epsilon_kw': args.epsilon, 'accepted': False,
                       'reason': 'EXTERNAL_TIMEOUT_NOT_PROOF_OF_INFEASIBILITY',
                       'solver_state': 'UNKNOWN'}
            finally:
                elapsed = time.perf_counter() - start
            rec['evaluation_elapsed_seconds'] = elapsed
            rec['external_timeout_seconds'] = args.timeout_seconds
            rec['solver_time_limit_seconds'] = args.solver_time_limit_seconds
        cache[key] = rec
        write_json_atomic(cache_path, cache)
        state['evaluations'] = list(cache.values())
        state['nondominated_accepted'] = non_dominated(state['evaluations'])
        write_json_atomic(out / 'summary.json', state)
        print(f"{len(cache):03d} | PV={d['pv_kw']:.1f} BESS={d['bess_kwh']:.1f} "
              f"PCS={d['pcs_kw']:.1f} | {rec['reason']}", flush=True)
        if is_indeterminate(rec):
            state['run_status'] = 'STOPPED_INDETERMINATE_EVALUATION'
            state['indeterminate_design'] = d
            write_json_atomic(out / 'summary.json', state)
            raise IndeterminateEvaluation(f"Candidato indeterminado: {key}; interrompendo NSGA-II sem penalidade de inviabilidade")
        return rec

    class R0Problem(ElementwiseProblem):
        def __init__(self):
            super().__init__(n_var=3, n_obj=2, n_ieq_constr=1,
                             xl=np.array([a for a, _ in BOUNDS]),
                             xu=np.array([b for _, b in BOUNDS]))

        def _evaluate(self, x, out_dict, *args_, **kwargs):
            rec = evaluate_candidate(x)
            if rec.get('accepted'):
                out_dict['F'] = [rec['f1_brl_per_pkm'], rec['f2_kw']]
                out_dict['G'] = [-1.]
            else:
                # Penalidade para orientar NSGA-II; NAO constitui F1/F2 fisico.
                pre = rec.get('analytical_prefilter') or {}
                violation = max(0., float(pre.get('max_power_deficit_kw', 0.)))
                out_dict['F'] = [1e6, 1e6]
                out_dict['G'] = [1. + violation]

    seeds = np.array([
        [1908.225, 30000., 16500.],
        [1908.225, 25000., 11000.],
        [1500., 30000., 12000.],
        [1908.225, 20000., 10000.],
    ], dtype=float)
    if args.population > 4:
        rng = np.random.default_rng(args.seed)
        extra = rng.uniform([0., 0., 0.], [1908.225, 30000., 16500.],
                            size=(args.population - 4, 3))
        seeds = np.vstack([seeds, extra])
    algorithm = NSGA2(pop_size=args.population, sampling=seeds,
                      eliminate_duplicates=True)
    print(f'INICIO NSGA-II | pop={args.population} geracoes={args.generations} '
          f'| cache={len(cache)} | escopo exploratorio', flush=True)
    try:
        minimize(R0Problem(), algorithm, ('n_gen', args.generations),
                 seed=args.seed, verbose=False)
    except IndeterminateEvaluation as exc:
        print(f'BUSCA_SUSPENSA: {exc}', file=sys.stderr, flush=True)
        return 3
    state['evaluations'] = list(cache.values())
    state['nondominated_accepted'] = non_dominated(state['evaluations'])
    state['completed'] = True
    state['run_status'] = 'COMPLETED'
    write_json_atomic(out / 'summary.json', state)
    print(f"FIM | avaliacoes unicas={len(cache)} | aceitas={sum(bool(r.get('accepted')) for r in cache.values())} "
          f"| nao dominadas aceitas={len(state['nondominated_accepted'])}")
    print(f"RELATORIO: {out / 'summary.json'}")


if __name__ == '__main__':
    sys.exit(main())
