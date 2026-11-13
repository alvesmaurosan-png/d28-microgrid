#!/usr/bin/env python3
"""REV16.1.3h: auditoria estatica de inclusao de factibilidade (sem solver).
Executar na raiz do repositorio. Somente leitura dos insumos; cria um JSON novo,
sem sobrescrever qualquer relatorio. Usa apenas biblioteca padrao Python.
"""
from __future__ import annotations
import ast
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
G1 = Path('results/D28_REV16_1_3c_G1_CONSOLIDADO.json')
G = Path('results/D28_REV16_1_3g_DIAGNOSTICO_EPS_2400.json')
OUT = Path('results/D28_REV16_1_3h_AUDITORIA_INCLUSAO_FACTIBILIDADE.json')
SOURCES = [
    Path('auditar_d28_rev16_1_3c.py'),
    Path('auditar_d28_rev16_1_3g.py'),
    Path('src/d28/optimization/economic_dispatch_f1f2.py'),
    Path('src/d28/optimization/biobjective_milp_connector.py'),
    Path('config/economics/r0_f1_exploratory_2026.json'),
]

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None

def main():
    out = ROOT / OUT
    if out.exists():
        print('BLOQUEADO: arquivo de saida ja existe; nenhuma sobrescrita:', out)
        return 4
    g1path, gpath = ROOT / G1, ROOT / G
    missing = [str(p) for p in (g1path, gpath) if not p.is_file()]
    if missing:
        print('BLOQUEADO: relatorios obrigatorios ausentes:', ', '.join(missing))
        return 3
    g1, g = read_json(g1path), read_json(gpath)
    rows = g1.get('rows', [])
    selected = {}
    issues = []
    for eps in (2300.0, 2400.0):
        found = [r for r in rows if isinstance(r, dict) and number(r.get('epsilon_kw')) == eps]
        if len(found) != 1:
            issues.append(f'G1: esperado um registro para epsilon={eps}, encontrados {len(found)}')
        else:
            selected[int(eps)] = found[0]
    comparisons = None
    if len(selected) == 2:
        a, b = selected[2300], selected[2400]
        ca, cb = number(a.get('milp_objective_brl')), number(b.get('milp_objective_brl'))
        pa, pb = number(a.get('f2_kw')), number(b.get('f2_kw'))
        if None in (ca, cb, pa, pb):
            issues.append('G1: custo MILP ou F2 nao numerico/finito')
        else:
            comparisons = {
                'epsilon_restrictive_kw': 2300.0,
                'epsilon_relaxed_kw': 2400.0,
                'g1_restrictive': {'milp_objective_brl': ca, 'f2_kw': pa, 'status': a.get('status'), 'checks': a.get('solver_checks')},
                'g1_relaxed': {'milp_objective_brl': cb, 'f2_kw': pb, 'status': b.get('status'), 'checks': b.get('solver_checks')},
                'delta_observed_cost_brl': cb - ca,
                'observed_cost_increase': cb > ca + 0.01,
                'restrictive_reported_f2_within_relaxed_epsilon': pa <= 2400.0 + 1e-5,
                'restrictive_reported_f2_within_own_epsilon': pa <= 2300.0 + 1e-5,
                'note': 'Pico agregado nao certifica a factibilidade de todas as restricoes.'
            }
            if a.get('status') != 'PASS' or b.get('status') != 'PASS':
                issues.append('G1: status diferente de PASS em um dos casos')
    solver = g.get('solver') or {}
    lo = number(solver.get('best_objective_bound'))
    hi = number(solver.get('best_feasible_objective'))
    info = solver.get('highs_info') or {}
    if not isinstance(info, dict):
        info = {}
    termination = solver.get('termination_condition')
    if number(g.get('epsilon_kw')) != 2400.0:
        issues.append('REV16.1.3g: epsilon diferente de 2400')
    if lo is None or hi is None or lo > hi + 1e-6:
        issues.append('REV16.1.3g: limites ausentes ou inconsistentes')
    if termination is None:
        issues.append('REV16.1.3g: termination_condition ausente')
    solver_evidence = {
        'epsilon_kw': g.get('epsilon_kw'),
        'termination_condition': termination,
        'time_limit_seconds': g.get('time_limit_seconds'),
        'best_feasible_objective_brl': hi,
        'best_objective_bound_brl': lo,
        'absolute_bound_gap_brl': (hi - lo) if hi is not None and lo is not None else None,
        'mip_gap': number(info.get('mip_gap')),
        'mip_node_count': info.get('mip_node_count'),
        'g1_2400_cost_within_reported_bounds': (
            lo - 0.01 <= comparisons['g1_relaxed']['milp_objective_brl'] <= hi + 0.01
            if comparisons and lo is not None and hi is not None else None),
        'optimality_certified': False,
        'note': 'Limites do solver aplicam-se a instancia efetivamente executada na REV16.1.3g.'
    }
    # Evidencia estatica: parseia os arquivos, mas nao executa codigo do projeto.
    structural = {'status': 'NOT_VERIFIED', 'checks': {}, 'limitations': []}
    try:
        economic_path = ROOT / SOURCES[2]
        audit_path = ROOT / SOURCES[0]
        econ_src = economic_path.read_text(encoding='utf-8-sig')
        audit_src = audit_path.read_text(encoding='utf-8-sig')
        econ_tree = ast.parse(econ_src)
        audit_tree = ast.parse(audit_src)
        solve_fn = next((n for n in econ_tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'solve_economic'), None)
        main_fn = next((n for n in audit_tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'main'), None)
        checks = structural['checks']
        checks['solve_economic_exists'] = solve_fn is not None
        if solve_fn:
            constraints = [n for n in ast.walk(solve_fn) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == 'rev05_epsilon' for t in n.targets)]
            constraint_text = [ast.get_source_segment(econ_src, n) or '' for n in constraints]
            checks['epsilon_constraint_grid_upper_bound'] = len(constraints) == 1 and any('mm.grid[t]<=epsilon_kw' in s.replace(' ', '') for s in constraint_text)
            objective = [n for n in ast.walk(solve_fn) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == 'rev05_economic_objective' for t in n.targets)]
            checks['economic_objective_without_explicit_epsilon'] = len(objective) == 1 and all('epsilon_kw' not in (ast.get_source_segment(econ_src, n) or '') for n in objective)
            checks['model_built_without_epsilon_argument'] = 'build_route_milp(route,design,inputs)' in re.sub(r'\s+', '', ast.get_source_segment(econ_src, solve_fn) or '')
        checks['g1_calls_solve_economic'] = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'solve_economic' for n in ast.walk(audit_tree))
        checks['g1_loops_over_epsilons'] = any(isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == 'eps' and isinstance(n.iter, ast.Attribute) and n.iter.attr == 'epsilons' for n in ast.walk(audit_tree))
        structural['status'] = 'STATIC_PATTERN_CHECKS_PASSED' if all(checks.values()) else 'STATIC_PATTERN_CHECKS_INCOMPLETE'
        structural['limitations'].append('Inspecao AST nao prova ausencia de mutacao interna em objetos compartilhados.')
        structural['limitations'].append('A comparacao de instancias geradas pelo Pyomo nao foi realizada.')
    except (OSError, SyntaxError, UnicodeError) as exc:
        issues.append(f'Inspecao estatica incompleta: {type(exc).__name__}: {exc}')
    provenance = {}
    for rel in [G1, G, *SOURCES]:
        p = ROOT / rel
        provenance[str(rel).replace('\\', '/')] = {'exists': p.is_file(), 'sha256': sha256(p) if p.is_file() else None}
        if not p.is_file():
            issues.append(f'Arquivo de proveniencia ausente: {rel}')
    report = {
        'revision': 'REV16.1.3h',
        'scope': 'R0_E100_FIXED_DESIGN_STATIC_FEASIBILITY_INCLUSION',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'classification': 'STRUCTURAL_FEASIBILITY_INCLUSION_CONDITIONAL_PRIMAL_REVALIDATION_NOT_PERFORMED',
        'status': 'AUDIT_WITH_LIMITATIONS' if not issues and structural['status'] == 'STATIC_PATTERN_CHECKS_PASSED' else 'INCOMPLETE_EVIDENCE',
        'execution_policy': {'solver_executed': False, 'production_files_modified': False, 'nsga2_authorized': False},
        'mathematical_claim': {
            'hypothesis': 'Todos os dados, parametros, objetivos e restricoes sao identicos, exceto grid[t] <= epsilon_kw.',
            'set_inclusion': 'F(2300) subset F(2400)',
            'optimal_cost_monotonicity': 'C*(2400) <= C*(2300)',
            'proof_scope': 'Propriedade condicional do problema matematico, nao certificacao de solucao historica.'
        },
        'g1_comparison': comparisons,
        'rev16_1_3g_solver_bounds': solver_evidence,
        'static_source_inspection': structural,
        'provenance_sha256': provenance,
        'limitations': [
            'Solucao primal completa historica nao localizada pela busca realizada; nenhuma revalidacao independente de todas as restricoes.',
            'Picos F2 e checks agregados do G1 nao substituem valores de todas as variaveis primais.',
            'Status PASS do G1 nao equivale a certificado independente de otimalidade global.',
            'REV16.1.3g encerrou por limite de tempo; gap residual nao nulo.',
            'A causa especifica do aumento de custo observado nao foi determinada.',
            'PKM/F1 permanecem sujeitos a homologacao separada; G1 nao os homologa.',
            'A auditoria nao altera G1/G2 nem libera NSGA-II.'
        ],
        'issues': issues,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    # Criacao exclusiva: impede sobrescrita ate em caso de corrida.
    try:
        with out.open('x', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, allow_nan=False)
            f.write('\n')
    except FileExistsError:
        print('BLOQUEADO: arquivo criado por outro processo; preservado:', out)
        return 4
    print('REV16.1.3h |', report['status'])
    print('STATIC_INSPECTION:', structural['status'])
    print('DELTA_G1_BRL:', comparisons['delta_observed_cost_brl'] if comparisons else None)
    print('G_BOUNDS_BRL:', lo, hi)
    print('ISSUES:', len(issues))
    for issue in issues:
        print(' -', issue)
    print('NSGA2_AUTHORIZED: False')
    print('REPORT:', out)
    return 0 if report['status'] == 'AUDIT_WITH_LIMITATIONS' else 2

if __name__ == '__main__':
    raise SystemExit(main())
