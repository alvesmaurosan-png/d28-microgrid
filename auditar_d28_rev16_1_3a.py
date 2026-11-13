#!/usr/bin/env python3
"""D28 REV16.1.3a: auditoria G1/G2 sem alterar o NSGA-II ou o MILP.

G1: reconcilia custos, despacho e F2 sem PKM homologado.
G2: exige evidência documental de homologação do PKM e calcula F1.

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


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def near(a, b, atol=1e-5, rtol=1e-9):
    return math.isclose(float(a), float(b), abs_tol=atol, rel_tol=rtol)


def positive(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def pkm_authorization(root, supplied):
    evidence_path = root / 'config/annual_f1_f2_evidence.json'
    economics_path = root / 'config/economics/r0_f1_exploratory_2026.json'
    objectives_path = root / 'config/experiments/r0_objective_inputs.json'
    files = [evidence_path, economics_path, objectives_path]
    if not all(p.is_file() for p in files):
        return None, 'MISSING_PKM_EVIDENCE_FILES', {}
    evidence, economics, objectives = map(load_json, files)
    hashes = {str(p.relative_to(root)): digest(p) for p in files}
    if evidence.get('annual_pkm_approved') is not True:
        return None, 'ANNUAL_PKM_NOT_APPROVED', hashes
    if economics.get('annual_pkm_status') != 'APPROVED':
        return None, 'ECONOMIC_PKM_STATUS_NOT_APPROVED', hashes
    vals = [economics.get('annual_pkm'), objectives.get('annual_pkm'), supplied]
    if not all(positive(v) for v in vals):
        return None, 'MISSING_OR_INVALID_PKM', hashes
    if not (near(vals[0], vals[1], atol=1e-6) and near(vals[0], vals[2], atol=1e-6)):
        return None, 'PKM_VALUE_MISMATCH', hashes
    return float(vals[0]), None, hashes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--gate', required=True, choices=['g1', 'g2'])
    ap.add_argument('--annual-pkm', type=float, default=None,
                    help='Obrigatório em G2; deve coincidir com os JSONs homologados')
    ap.add_argument('--epsilons', type=float, nargs='+', default=[2500, 2450, 2400, 2300])
    ap.add_argument('--pv-kw', type=float, default=1908.225)
    ap.add_argument('--bess-kwh', type=float, default=15000)
    ap.add_argument('--pcs-kw', type=float, default=5500)
    args = ap.parse_args()

    if args.gate == 'g1' and args.annual_pkm is not None:
        ap.error('G1 não aceita --annual-pkm: o denominador permanece bloqueado')
    if args.gate == 'g2' and not positive(args.annual_pkm):
        ap.error('G2 exige --annual-pkm positivo, finito e homologado')
    if not args.epsilons or any(not positive(v) or v > 2500 for v in args.epsilons):
        ap.error('epsilons devem estar em (0,2500]')
    if any(not math.isfinite(v) or v < 0 for v in (args.pv_kw, args.bess_kwh, args.pcs_kw)):
        ap.error('dimensionamento não negativo e finito obrigatório')
    if args.pcs_kw > 0.55 * args.bess_kwh + 1e-8:
        ap.error('PCS excede 0,55 * capacidade BESS')

    out = ROOT / 'results' / f'D28_REV16_1_3a_{args.gate.upper()}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {'revision': 'REV16.1.3a', 'gate': args.gate.upper(),
              'classification': 'EXPLORATORY_NOT_HOMOLOGATED',
              'status': 'PENDING', 'rows': [], 'limitations': [
                  'PASS valida identidades e verificações disponíveis, não homologa tarifa nem formulação econômica.',
                  'A equivalência entre objetivo interno do MILP e custo econômico total exige auditoria separada.'
              ]}

    if args.gate == 'g2':
        annual_pkm, reason, hashes = pkm_authorization(ROOT, args.annual_pkm)
        report['pkm_evidence_sha256'] = hashes
        if reason:
            report.update(status='BLOCKED', reason=reason,
                          message='PKM não homologado ou divergente; nenhuma otimização foi executada')
            out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            print(json.dumps({'gate':'G2','status':'BLOCKED','reason':reason,'report':str(out)}, ensure_ascii=False))
            return 3
    else:
        annual_pkm = None

    x, series_path, start = base.inputs()
    cfg_path = ROOT / 'config/economics/r0_f1_exploratory_2026.json'
    cfg = base.Economics.from_json(cfg_path)
    design = {'pv_kw': args.pv_kw, 'bess_kwh': args.bess_kwh, 'pcs_kw': args.pcs_kw}
    if args.pv_kw > float(cfg.pv_capacity_max_kwp) + 1e-6:
        ap.error('PV excede teto geométrico')
    if not near(x.pcc_cap_kw, 2500, atol=1e-7):
        raise RuntimeError('PCC físico inesperado')
    if len(x.load_kw) != 35040 or not near(x.dt_hours, 0.25, atol=1e-12):
        raise RuntimeError('Série anual de 15 minutos inválida')

    report['provenance'] = {'series_sha256': digest(series_path),
                            'economics_sha256': digest(cfg_path), 'year': start.year,
                            'design': design, 'annual_pkm': annual_pkm,
                            'scope': 'R0/E100, fixed design, epsilon diagnostics; NSGA-II not run'}
    prices = base.EnergyPrices(grid_brl_kwh=(float(cfg.energy_tariff_brl_per_kwh),) * len(x.load_kw))
    for eps in args.epsilons:
        print(f'GATE {args.gate.upper()} | epsilon={eps:.3f} kW', flush=True)
        row = {'epsilon_kw': eps, 'status': 'PENDING'}
        try:
            r = base.solve_economic('R0', design, x, prices, epsilon_kw=eps, solver_name='appsi_highs')
            row.update(status=r.get('status'), solver_reason=r.get('reason'),
                       solver_checks=r.get('checks'))
            if r.get('status') != 'PASS':
                row['gate'] = 'INFEASIBLE_OR_SOLVER_FAILED'
            else:
                grid = r['grid_kw']
                bill = base.temporal_bill(grid, prices.grid_brl_kwh, x.months, x.dt_hours,
                                          cfg.demand_tariff_brl_per_kw_month)
                # A API present_value requer annual_pkm mesmo para retornar somente VP(custos).
                # G1 usa sentinelas 1 e 2 EXCLUSIVAMENTE para verificar independência do numerador;
                # nunca reporta VP(PKM) nem F1 a partir dessas sentinelas.
                cap = base.present_value(cfg, design['pv_kw'], design['bess_kwh'],
                    design['pcs_kw'], annual_variable_bill_brl=bill['total_brl'],
                    annual_pkm=annual_pkm if annual_pkm is not None else 1.0)
                cap_alt = None
                if args.gate == 'g1':
                    cap_alt = base.present_value(cfg, design['pv_kw'], design['bess_kwh'],
                        design['pcs_kw'], annual_variable_bill_brl=bill['total_brl'], annual_pkm=2.0)
                f2 = max(grid)
                peaks = bill['monthly_peaks_kw']
                monthly = list(peaks.values()) if isinstance(peaks, dict) else list(peaks)
                checks = {
                    'f2_matches_solver': near(f2, r['pilot_f2_kw']),
                    'f2_within_epsilon': f2 <= eps + 1e-5,
                    'f2_matches_monthly_peaks': bool(monthly) and near(f2, max(monthly)),
                    'energy_bill_matches_solver_grid_cost': near(bill['energy_brl'], r['cost_components_brl']['grid_brl']),
                    'total_bill_identity': near(bill['total_brl'], bill['energy_brl'] + bill['demand_brl']),
                    'demand_bill_identity': near(bill['demand_brl'], sum(monthly) * float(cfg.demand_tariff_brl_per_kw_month)),
                    'native_solver_checks': bool(r.get('checks')) and all(r['checks'].values()),
                    'pv_cost_finite_nonnegative': math.isfinite(cap['pv_total_cost_brl']) and cap['pv_total_cost_brl'] >= 0,
                }
                if cap_alt is not None:
                    checks['pv_cost_independent_of_pkm'] = near(cap['pv_total_cost_brl'], cap_alt['pv_total_cost_brl'])
                row.update(f2_kw=f2, grid_energy_kwh=r['grid_energy_kwh'],
                           annual_energy_charge_brl=bill['energy_brl'],
                           annual_demand_charge_brl=bill['demand_brl'],
                           annual_energy_total_brl=bill['total_brl'],
                           pv_total_cost_brl=cap['pv_total_cost_brl'],
                           monthly_peaks_kw=peaks, checks=checks)
                if args.gate == 'g2':
                    f1 = cap['pv_total_cost_brl'] / cap['pv_pkm']
                    checks['f1_identity'] = positive(cap['pv_pkm']) and near(f1 * cap['pv_pkm'], cap['pv_total_cost_brl'])
                    row.update(pv_pkm=cap['pv_pkm'], f1_brl_per_pkm=f1)
                else:
                    row.update(f1_brl_per_pkm=None, pv_pkm=None,
                               f1_status='BLOCKED_PENDING_PKM_HOMOLOGATION')
                row['gate'] = 'PASS' if all(checks.values()) else 'REVIEW'
        except Exception as exc:
            row.update(status='ERROR', gate='REVIEW', error_type=type(exc).__name__, error=str(exc))
        report['rows'].append(row)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        print(json.dumps({k:row.get(k) for k in ('epsilon_kw','status','f2_kw','f1_brl_per_pkm','gate','error')}, ensure_ascii=False), flush=True)

    if all(r['gate'] == 'PASS' for r in report['rows']):
        report['status'] = 'PASS_ACCOUNTING_CHECKS_ONLY'
    else:
        report['status'] = 'REVIEW'
    report['g2_eligibility'] = 'PKM_VALIDATED' if args.gate == 'g2' else 'NOT_EVALUATED'
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    print('STATUS FINAL:', report['status'])
    print('RELATÓRIO:', out)
    return 0 if report['status'] == 'PASS_ACCOUNTING_CHECKS_ONLY' else 2


if __name__ == '__main__':
    sys.exit(main())
