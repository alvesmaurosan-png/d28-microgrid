#!/usr/bin/env python3
"""D28 REV16.1.3 — gate de reconciliação econômica F1/F2, sem modificar módulos.
Executar na raiz do repositório REV16.1 com Python 3.11.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
import rodar_d28_rev16_1 as base


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a, b, atol=1e-5, rtol=1e-9):
    return math.isclose(float(a), float(b), abs_tol=atol, rel_tol=rtol)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--annual-pkm', type=float, required=True)
    ap.add_argument('--epsilons', type=float, nargs='+', default=[2500, 2450, 2400, 2300])
    ap.add_argument('--pv-kw', type=float, default=1908.225)
    ap.add_argument('--bess-kwh', type=float, default=15000)
    ap.add_argument('--pcs-kw', type=float, default=5500)
    args = ap.parse_args()
    if not math.isfinite(args.annual_pkm) or args.annual_pkm <= 0:
        ap.error('PKM anual deve ser positivo e finito')
    if not args.epsilons or any(not math.isfinite(v) or v <= 0 or v > 2500 for v in args.epsilons):
        ap.error('epsilons devem estar em (0,2500]')
    if min(args.pv_kw, args.bess_kwh, args.pcs_kw) < 0 or args.pcs_kw > .55 * args.bess_kwh + 1e-8:
        ap.error('dimensionamento invalido')

    x, series_path, start = base.inputs()
    cfg_path = ROOT / 'config/economics/r0_f1_exploratory_2026.json'
    cfg = base.Economics.from_json(cfg_path)
    design = {'pv_kw': args.pv_kw, 'bess_kwh': args.bess_kwh, 'pcs_kw': args.pcs_kw}
    if args.pv_kw > float(cfg.pv_capacity_max_kwp) + 1e-6:
        ap.error('PV excede teto geometrico')
    if not close(x.pcc_cap_kw, 2500, atol=1e-7):
        raise RuntimeError('PCC fisico inesperado')
    if len(x.load_kw) != 35040 or not close(x.dt_hours, .25, atol=1e-12):
        raise RuntimeError('Serie anual de 15 min invalida')

    prices = base.EnergyPrices(grid_brl_kwh=(float(cfg.energy_tariff_brl_per_kwh),) * len(x.load_kw))
    provenance = {'revision':'REV16.1.3', 'classification':'EXPLORATORY_NOT_HOMOLOGATED',
                  'series_sha256':sha256(series_path), 'economics_sha256':sha256(cfg_path),
                  'series_path':str(series_path), 'economics_path':str(cfg_path),
                  'year':start.year, 'annual_pkm':args.annual_pkm,
                  'scope':'R0/E100; fixed design; epsilon-constraint diagnostic; no NSGA-II'}
    output = {'provenance':provenance, 'design':design, 'rows':[], 'gate':'PENDING'}
    out_path = ROOT / 'results' / 'D28_REV16_1_3_GATE_ECONOMICO.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)

    for eps in args.epsilons:
        print(f'TESTE epsilon={eps:.3f} kW', flush=True)
        r = base.solve_economic('R0', design, x, prices, epsilon_kw=eps, solver_name='appsi_highs')
        row = {'epsilon_kw':eps, 'status':r.get('status'), 'solver_reason':r.get('reason'),
               'solver_checks':r.get('checks')}
        if r.get('status') == 'PASS':
            grid = r['grid_kw']
            bill = base.temporal_bill(grid, prices.grid_brl_kwh, x.months, x.dt_hours,
                                      cfg.demand_tariff_brl_per_kw_month)
            cap = base.present_value(cfg, design['pv_kw'], design['bess_kwh'], design['pcs_kw'],
                                     annual_variable_bill_brl=bill['total_brl'],
                                     annual_pkm=args.annual_pkm)
            f2 = max(grid)
            f1 = cap['pv_total_cost_brl'] / cap['pv_pkm']
            monthly = bill['monthly_peaks_kw']
            if isinstance(monthly, dict):
                monthly_vals = list(monthly.values())
            else:
                monthly_vals = list(monthly)
            checks = {
                'f2_equals_grid_max':close(f2, r['pilot_f2_kw']),
                'f2_within_epsilon':f2 <= eps + 1e-5,
                'f2_equals_max_monthly_peak':close(f2, max(monthly_vals)),
                'bill_energy_equals_grid_operating_cost':close(bill['energy_brl'], r['cost_components_brl']['grid_brl']),
                'bill_total_equals_energy_plus_demand':close(bill['total_brl'], bill['energy_brl'] + bill['demand_brl']),
                'demand_equals_monthly_peak_sum_times_tariff':close(
                    bill['demand_brl'], sum(monthly_vals)*float(cfg.demand_tariff_brl_per_kw_month)),
                'present_value_identity':close(f1*cap['pv_pkm'], cap['pv_total_cost_brl']),
                'native_solver_checks':all(r['checks'].values()),
            }
            row.update(f1_brl_per_pkm=f1, f2_kw=f2,
                       annual_energy_kwh=r['grid_energy_kwh'],
                       variable_operating_cost_brl=r['cost_brl'],
                       annual_energy_charge_brl=bill['energy_brl'],
                       annual_demand_charge_brl=bill['demand_brl'],
                       annual_energy_total_brl=bill['total_brl'],
                       monthly_peaks_kw=monthly,
                       present_energy_cost_brl=cap['pv_total_cost_brl'],
                       present_pkm=cap['pv_pkm'], checks=checks,
                       gate='PASS' if all(checks.values()) else 'REVIEW')
        else:
            row['gate'] = 'INFEASIBLE_OR_SOLVER_FAILED'
        output['rows'].append(row)
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        print(json.dumps({k:row.get(k) for k in ('epsilon_kw','status','f1_brl_per_pkm','f2_kw','gate','checks')},
                         ensure_ascii=False, default=str), flush=True)

    output['gate'] = 'PASS' if all(r['gate'] == 'PASS' for r in output['rows']) else 'REVIEW'
    output['interpretation'] = ('PASS validates accounting identities under current exploratory tariff model, '
                                'NOT contractual adequacy or economic homologation')
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    print('GATE FINAL:', output['gate'])
    print('RELATORIO:', out_path)
    if output['gate'] != 'PASS':
        raise SystemExit(2)

if __name__ == '__main__':
    main()
