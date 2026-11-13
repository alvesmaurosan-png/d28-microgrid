#!/usr/bin/env python3
"""Patch numérico controlado G3: testa, depois executa somente candidato 3.
Não modifica runner original, cache G3 nem módulo econômico.
"""
import argparse
import ast
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / 'rodar_d28_rev16_1.py'
CACHE = ROOT / 'results/D28_G3_CACHE.json'
OUTPUTS = [ROOT / 'results/D28_REV16_1_R0_E100_ANUAL.json',
           ROOT / 'results/D28_REV16_1_R0_E100_GRID_15MIN.csv']
TOL = 1e-6


def reconcile_grid(values, tol=TOL):
    """Remove somente resíduos negativos em [-tol, 0); rejeita erros reais."""
    clean = []
    count = 0
    smallest = 0.0
    for i, raw in enumerate(values):
        v = float(raw)
        if not math.isfinite(v):
            raise ValueError(f'INVALID_GRID_KW_NONFINITE index={i} value={v}')
        if v < -tol:
            raise ValueError(f'INVALID_GRID_KW_NEGATIVE index={i} value={v} tolerance={tol}')
        if v < 0:
            count += 1
            smallest = min(smallest, v)
            v = 0.0
        clean.append(v)
    return clean, {'n_corrected': count, 'min_original_negative_kw': smallest,
                   'tolerance_kw': tol}


def tests():
    checks = []
    def ok(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    v, d = reconcile_grid([0, 1, -5.115907697472721e-12, -TOL, 2500])
    ok('residuos pequenos e fronteira inclusiva', v == [0, 1, 0, 0, 2500] and d['n_corrected'] == 2)
    v, d = reconcile_grid([0, 3.0, 2500.0])
    ok('valores validos inalterados', v == [0, 3.0, 2500.0] and d['n_corrected'] == 0)
    for name, bad in [('negativo significativo', -1e-3),
                      ('abaixo da tolerancia', -1.0001e-6),
                      ('NaN', float('nan')), ('infinito positivo', float('inf')),
                      ('infinito negativo', -float('inf'))]:
        try:
            reconcile_grid([1, bad])
        except ValueError:
            checks.append(name)
        else:
            raise AssertionError(name + ' foi indevidamente aceito')
    original = [0, -5.115907697472721e-12, 10]
    fixed, _ = reconcile_grid(original)
    ok('serie original nao mutada', original[1] < 0 and fixed[1] == 0)
    return checks


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def build_runner():
    src = RUNNER.read_text(encoding='utf-8-sig')
    pattern = r'(?m)^(?P<indent>[ \t]*)bill\s*=\s*temporal_bill\s*\(\s*result\["grid_kw"\]'
    matches = list(re.finditer(pattern, src))
    if len(matches) != 1:
        raise RuntimeError(f'Esperada 1 chamada temporal_bill, encontradas {len(matches)}')
    m = matches[0]
    indent = m.group('indent')
    # Normaliza somente a série de importação; todos os cálculos posteriores
    # (F1, F2 e exportação) devem consumir a mesma série.
    injection = '\n'.join(indent + s for s in [
        '# G3_NUMERIC_RECONCILIATION_REV16_1_3d',
        'from d28_rev16_1_3d_correcao_g3 import reconcile_grid as _g3_reconcile',
        '_g3_grid, _g3_reconciliation = _g3_reconcile(result["grid_kw"])',
        'result["grid_kw"] = _g3_grid',
        'result["pilot_f2_kw"] = max(_g3_grid)',
        'result["grid_energy_kwh"] = sum(_g3_grid) * 0.25',
        'print("G3_RECONCILIACAO_NUMERICA=" + json.dumps(_g3_reconciliation), flush=True)',
    ]) + '\n'
    patched = src[:m.start()] + injection + src[m.start():]
    ast.parse(patched)
    return patched


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--timeout-seconds', type=int, default=3600)
    p.add_argument('--test-only', action='store_true')
    args = p.parse_args()
    passed = tests()
    print(f'TESTES DE FRONTEIRA: PASS ({len(passed)}/{len(passed)})', flush=True)
    for name in passed:
        print('  PASS:', name, flush=True)
    if args.test_only:
        return
    if args.timeout_seconds <= 0:
        p.error('timeout deve ser positivo')
    if not RUNNER.is_file():
        p.error('Runner original ausente; coloque este script na raiz do repositório')
    patched = build_runner()
    temp = ROOT / '_d28_runner_g3_REV16_1_3d_TEMP.py'
    if temp.exists():
        raise RuntimeError('Runner temporário já existe: ' + str(temp))
    folder = ROOT / 'results/G3_correcao_numerica' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True)
    backups = {}
    for output in OUTPUTS:
        if output.exists():
            backup = folder / ('ANTES_' + output.name)
            shutil.copy2(output, backup)
            backups[output] = backup
        else:
            backups[output] = None
    original_runner_hash = sha(RUNNER)
    original_cache_hash = sha(CACHE)
    log = folder / 'execucao.log'
    returncode = None
    try:
        temp.write_text(patched, encoding='utf-8')
        cmd = [sys.executable, str(temp), '--pv-kw', '1908.225',
               '--bess-kwh', '30000', '--pcs-kw', '5500', '--annual-pkm', '137675700']
        print('Executando exclusivamente candidato 3, MILP anual...', flush=True)
        with log.open('w', encoding='utf-8') as f:
            try:
                proc = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                                      timeout=args.timeout_seconds, check=False)
                returncode = proc.returncode
            except subprocess.TimeoutExpired:
                returncode = 'TIMEOUT'
        for output in OUTPUTS:
            if output.exists():
                shutil.copy2(output, folder / ('DEPOIS_' + output.name))
    finally:
        for output, backup in backups.items():
            if backup is None:
                if output.exists():
                    output.unlink()
            else:
                shutil.copy2(backup, output)
        if temp.exists():
            temp.unlink()
        summary = {
            'revision': 'REV16.1.3d_G3_NUMERIC', 'candidate': 3,
            'tests_passed': passed, 'runner_returncode': returncode,
            'runner_original_unchanged': sha(RUNNER) == original_runner_hash,
            'cache_unchanged': sha(CACHE) == original_cache_hash,
            'outputs_restored': True, 'log': str(log),
            'classification': 'EXPLORATORY_NOT_HOMOLOGATED'
        }
        (folder / 'resumo.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print('RETORNO RUNNER:', returncode)
    for line in log.read_text(encoding='utf-8', errors='replace').splitlines():
        if any(s in line for s in ('G3_RECONCILIACAO_NUMERICA=', '"status":', '"f1_brl_per_pkm":',
                                  '"f2_kw":', 'Traceback', 'ValueError:', 'Relatorio:')):
            print(line[:2000])
    print('RUNNER PRESERVADO:', summary['runner_original_unchanged'])
    print('CACHE PRESERVADO:', summary['cache_unchanged'])
    print('SAIDAS ORIGINAIS RESTAURADAS:', summary['outputs_restored'])
    print('EVIDENCIAS:', folder)
    if returncode != 0:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
