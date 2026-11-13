#!/usr/bin/env python3
"""D28 REV16.1.2: F1 custo da energia por passageiro-km; F2 pico PCC.
Dominio computacional adaptativo para BESS/PCS; sem mudar MILP ou economia base.
"""
import argparse
import hashlib
import inspect
import json
import math
from pathlib import Path

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
import rodar_d28_rev16_1 as base

ROOT = Path(__file__).resolve().parent
C_RATE = 0.55
PCC = 2500.0
SEED_DESIGN = (1908.225, 15000.0, 5500.0)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def call_base(design, x, cfg, annual_pkm, provenance):
    signature = inspect.signature(base.run)
    if 'c_rate' in signature.parameters:
        return base.run(design, x, cfg, annual_pkm, provenance, c_rate=C_RATE)
    if len(signature.parameters) == 6:
        return base.run(design, x, cfg, annual_pkm, provenance, C_RATE)
    if len(signature.parameters) == 5:
        return base.run(design, x, cfg, annual_pkm, provenance)
    raise RuntimeError(f'Assinatura nao reconhecida de base.run: {signature}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--annual-pkm', type=float, required=True)
    ap.add_argument('--population', type=int, default=12)
    ap.add_argument('--generations', type=int, default=3)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--bess-ceiling-kwh', type=float, default=15000.0)
    ap.add_argument('--pcs-ceiling-kw', type=float, default=5500.0)
    ap.add_argument('--expansion-factor', type=float, default=1.5)
    ap.add_argument('--max-expansions', type=int, default=2)
    ap.add_argument('--boundary-fraction', type=float, default=0.95)
    args = ap.parse_args()
    if not math.isfinite(args.annual_pkm) or args.annual_pkm <= 0:
        ap.error('annual-pkm deve ser positivo e documentado')
    if args.population < 4 or args.generations < 1 or args.max_expansions < 0:
        ap.error('Parametros de evolucao invalidos')
    if args.expansion_factor <= 1 or not 0 < args.boundary_fraction < 1:
        ap.error('Fator de expansao ou limiar de fronteira invalidos')
    if args.bess_ceiling_kwh < 15000 or args.pcs_ceiling_kw < 5500:
        ap.error('Dominio inicial deve conter a semente PASS de 15 MWh / 5,5 MW')

    x, series_path, start = base.inputs()
    cfg_path = ROOT / 'config/economics/r0_f1_exploratory_2026.json'
    cfg = base.Economics.from_json(cfg_path)
    pv_max = float(cfg.pv_capacity_max_kwp)
    if abs(float(x.pcc_cap_kw) - PCC) > 1e-8:
        raise RuntimeError('PCC divergente de 2500 kW')
    if abs(pv_max - SEED_DESIGN[0]) > 1e-6:
        raise RuntimeError('Teto geometrico PV mudou; reconciliar antes de executar')
    if len(x.load_kw) != 35040 or abs(x.dt_hours - .25) > 1e-12:
        raise RuntimeError('Serie anual de 15 minutos inconsistente')
    provenance = {
        'revision': 'REV16.1.2', 'scenario': 'R0/E100',
        'f1_definition': 'Custo da Energia por Passageiro-Quilometro',
        'f1_unit': 'BRL/passageiro-km', 'f2_definition': 'Pico de importacao no PCC',
        'f2_unit': 'kW', 'annual_pkm': args.annual_pkm,
        'pv_geometric_ceiling_kwp': pv_max, 'pcc_limit_kw': PCC,
        'bess_pcs_bounds': 'adaptive_computational_not_physical',
        'physical_model_changed': False, 'economics_model_changed': False,
        'classification': 'EXPLORATORY_NOT_HOMOLOGATED',
        'series': str(series_path), 'series_sha256': digest(series_path),
        'economics': str(cfg_path), 'economics_sha256': digest(cfg_path),
        'year': start.year,
    }
    load = np.asarray(x.load_kw, dtype=float)
    pv_pu = np.asarray(x.pv_pu, dtype=float)
    required_cache = {}
    def required_pcs(pv):
        key = round(pv, 7)
        if key not in required_cache:
            required_cache[key] = max(0.0, float(np.max(load - PCC - pv * pv_pu)))
        return required_cache[key]

    cache = {}
    all_rounds = []
    bess_max = args.bess_ceiling_kwh
    pcs_max = args.pcs_ceiling_kw
    seed_design = np.array(SEED_DESIGN, dtype=float)
    previous_feasible = [seed_design]
    output_dir = ROOT / 'results'
    output_dir.mkdir(exist_ok=True)

    for round_id in range(args.max_expansions + 1):
        rng = np.random.default_rng(args.seed + round_id)
        initial = [seed_design.tolist()]
        for old in previous_feasible:
            if len(initial) >= args.population:
                break
            v = np.asarray(old, dtype=float)
            if not np.allclose(v, seed_design) and v[1] <= bess_max and v[2] <= pcs_max:
                initial.append(v.tolist())
        attempts = 0
        while len(initial) < args.population and attempts < 10000:
            attempts += 1
            pv = float(rng.uniform(.85 * pv_max, pv_max))
            bess = float(rng.uniform(.72 * bess_max, bess_max))
            required = required_pcs(pv)
            upper = min(pcs_max, C_RATE * bess)
            if required > upper:
                continue
            pcs = float(rng.uniform(required, upper)) if required < upper else upper
            candidate = [pv, bess, pcs]
            if not any(np.allclose(candidate, s, atol=1e-6) for s in initial):
                initial.append(candidate)
        if len(initial) < args.population:
            raise RuntimeError('Nao foi possivel gerar populacao inicial admissivel em potencia')
        records = []
        class Problem(ElementwiseProblem):
            def __init__(self):
                super().__init__(n_var=3, n_obj=2, n_ieq_constr=1,
                                 xl=np.array([0., 0., 0.]),
                                 xu=np.array([pv_max, bess_max, pcs_max]))
            def _evaluate(self, z, out, *unused, **kw):
                pv, bess, pcs = (float(v) for v in z)
                required = required_pcs(pv)
                violation = max(0., required - pcs, pcs - C_RATE * bess)
                if violation > 1e-7:
                    records.append({'design': [pv,bess,pcs], 'status': 'PRECHECK_INFEASIBLE',
                                    'constraint_violation_kw': violation})
                    out['F'] = [1e15, 1e15]
                    out['G'] = [violation]
                    return
                key = tuple(round(v, 7) for v in (pv,bess,pcs))
                if key not in cache:
                    cache[key] = call_base({'pv_kw':pv, 'bess_kwh':bess, 'pcs_kw':pcs},
                                           x, cfg, args.annual_pkm, provenance)
                result = cache[key]
                row = {'design': [pv,bess,pcs], 'status': result.get('status'),
                       'solver_reason': result.get('solver_reason'),
                       'f1_brl_per_pkm': result.get('f1_brl_per_pkm'),
                       'f2_kw': result.get('f2_kw')}
                if result.get('status') == 'PASS':
                    f1 = result.get('f1_brl_per_pkm')
                    f2 = result.get('f2_kw')
                    cost = result.get('present_energy_cost_brl')
                    discounted_pkm = result.get('discounted_pkm')
                    if not all(isinstance(v, (int,float)) and math.isfinite(v)
                               for v in (f1,f2,cost,discounted_pkm)):
                        raise RuntimeError('F1/F2/VP(custo energia)/VP(PKM) invalidos')
                    if discounted_pkm <= 0 or abs(f1 - cost / discounted_pkm) > 1e-9:
                        raise RuntimeError('F1 nao corresponde a VP(custo da energia)/VP(PKM)')
                    if f2 > PCC + 1e-5 or f2 < -1e-5:
                        raise RuntimeError('F2 viola o limite PCC')
                    row.update(present_energy_cost_brl=cost, discounted_pkm=discounted_pkm)
                    out['F'] = [f1,f2]
                    out['G'] = [-1.]
                else:
                    out['F'] = [1e15,1e15]
                    out['G'] = [1.]
                records.append(row)
                print(f'RODADA {round_id} AVALIACAO {len(records)}: '
                      f'{row["status"]} F1={row.get("f1_brl_per_pkm")} '
                      f'F2={row.get("f2_kw")}', flush=True)

        print(f'RODADA {round_id}: BESS <= {bess_max:.1f} kWh, '
              f'PCS <= {pcs_max:.1f} kW (limites computacionais)', flush=True)
        result = minimize(Problem(), NSGA2(pop_size=args.population,
                          sampling=np.asarray(initial, dtype=float),
                          eliminate_duplicates=True), ('n_gen', args.generations),
                          seed=args.seed + round_id, verbose=True)
        pareto = result.F.tolist() if result.F is not None else []
        designs = np.atleast_2d(result.X).tolist() if result.X is not None else []
        feasible = [r['design'] for r in records if r['status'] == 'PASS']
        previous_feasible = feasible[-args.population:] or [seed_design]
        touches = [d for d in designs if
                   d[1] >= args.boundary_fraction * bess_max or
                   d[2] >= args.boundary_fraction * pcs_max]
        round_report = {'round':round_id, 'bess_computational_ceiling_kwh':bess_max,
                        'pcs_computational_ceiling_kw':pcs_max,
                        'initial_population':initial, 'evaluations':records,
                        'pareto_f1_f2':pareto, 'pareto_designs':designs,
                        'n_feasible_evaluations':len(feasible),
                        'n_pareto_near_computational_boundary':len(touches)}
        all_rounds.append(round_report)
        path = output_dir / 'D28_REV16_1_2_R0_E100_NSGA2.json'
        path.write_text(json.dumps({'provenance':provenance,'rounds':all_rounds},
                         ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        print('RELATORIO:', path, flush=True)
        if not touches:
            print('SEM TOQUE NO TETO computacional na frente desta rodada. '
                  'Nao constitui prova de otimalidade global.', flush=True)
            break
        if round_id < args.max_expansions:
            print('Fronteira proxima de teto computacional: expandindo dominio.', flush=True)
            bess_max *= args.expansion_factor
            pcs_max *= args.expansion_factor
        else:
            print('ATENCAO: expansoes esgotadas com fronteira proxima ao teto.', flush=True)

if __name__ == '__main__':
    main()
