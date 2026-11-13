#!/usr/bin/env python3
"""G3: diagnóstico isolado do candidato 3, sem modificar runner, cache ou saídas preexistentes."""
import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "rodar_d28_rev16_1.py"
CACHE = ROOT / "results/D28_G3_CACHE.json"
OUTPUTS = [ROOT / "results/D28_REV16_1_R0_E100_ANUAL.json",
           ROOT / "results/D28_REV16_1_R0_E100_GRID_15MIN.csv"]
PKM = 137675700

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()
    if not RUNNER.exists():
        parser.error("Coloque este arquivo na raiz, junto de rodar_d28_rev16_1.py")
    source = RUNNER.read_text(encoding="utf-8-sig")
    pattern = r'(?m)^(?P<indent>[ \t]*)bill\s*=\s*temporal_bill\s*\(\s*result\["grid_kw"\]'
    matches = list(re.finditer(pattern, source))
    if len(matches) != 1:
        raise RuntimeError(f"Esperada uma chamada temporal_bill; encontradas {len(matches)}")
    match = matches[0]
    indent = match.group("indent")
    diagnostic = """
import math as _g3_math
_g3_values = [float(v) for v in result["grid_kw"]]
_g3_bad = [(i, v) for i, v in enumerate(_g3_values)
           if not _g3_math.isfinite(v) or v < 0]
_g3_negative = [(i, v) for i, v in _g3_bad if _g3_math.isfinite(v)]
_g3_finite = [v for v in _g3_values if _g3_math.isfinite(v)]
_g3_report = {
    "n": len(_g3_values),
    "n_negative": len(_g3_negative),
    "n_nonfinite": len(_g3_bad) - len(_g3_negative),
    "min_finite_kw": min(_g3_finite) if _g3_finite else None,
    "max_finite_kw": max(_g3_finite) if _g3_finite else None,
    "min_negative_kw": min((v for _, v in _g3_negative), default=None),
    "first_invalid": [(i, repr(v)) for i, v in _g3_bad[:30]],
    "negative_below_minus_1e-6": sum(v < -1e-6 for _, v in _g3_negative),
    "negative_between_minus_1e-6_and_zero": sum(-1e-6 <= v < 0 for _, v in _g3_negative)
}
print("G3_DIAGNOSTICO_GRID_KW=" + __import__("json").dumps(_g3_report), flush=True)
"""
    injection = "".join(indent + line + "\n" for line in diagnostic.strip().splitlines())
    patched = source[:match.start()] + injection + source[match.start():]
    ast.parse(patched)
    folder = ROOT / "results/G3_diagnostico" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder.mkdir(parents=True)
    temp = ROOT / "_d28_runner_g3_DIAGNOSTICO_TEMP.py"
    if temp.exists():
        raise RuntimeError(f"Arquivo temporário já existe: {temp}")
    before_runner, before_cache = sha(RUNNER), sha(CACHE)
    backups = {}
    for output in OUTPUTS:
        backup = folder / ("ANTES_" + output.name)
        if output.exists():
            shutil.copy2(output, backup)
            backups[output] = backup
        else:
            backups[output] = None
    log = folder / "execucao.log"
    exit_code = None
    try:
        temp.write_text(patched, encoding="utf-8")
        cmd = [sys.executable, str(temp), "--pv-kw", "1908.225",
               "--bess-kwh", "30000", "--pcs-kw", "5500",
               "--annual-pkm", str(PKM)]
        print("Executando diagnóstico G3 do candidato 3 (30 MWh)...", flush=True)
        with log.open("w", encoding="utf-8") as stream:
            try:
                completed = subprocess.run(cmd, cwd=ROOT, stdout=stream,
                                           stderr=subprocess.STDOUT,
                                           timeout=args.timeout_seconds, check=False)
                exit_code = completed.returncode
            except subprocess.TimeoutExpired:
                exit_code = "TIMEOUT"
        for output in OUTPUTS:
            if output.exists():
                shutil.copy2(output, folder / ("DEPOIS_" + output.name))
    finally:
        for output, backup in backups.items():
            if backup is not None:
                shutil.copy2(backup, output)
            elif output.exists():
                output.unlink()
        if temp.exists():
            temp.unlink()
        summary = {"exit_code": exit_code,
                   "runner_unchanged": before_runner == sha(RUNNER),
                   "cache_unchanged": before_cache == sha(CACHE),
                   "outputs_restored": True,
                   "log": str(log)}
        (folder / "resumo.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n--- RESULTADO DO DIAGNOSTICO ---")
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if "G3_DIAGNOSTICO_GRID_KW=" in line or "Traceback" in line or "ValueError:" in line or "status" in line:
            print(line[:2000])
    print("Retorno:", exit_code)
    print("Runner original preservado:", summary["runner_unchanged"])
    print("Cache preservado:", summary["cache_unchanged"])
    print("Saídas restauradas:", summary["outputs_restored"])
    print("Log completo:", log)
    print("Pasta de evidências:", folder)

if __name__ == "__main__":
    main()
