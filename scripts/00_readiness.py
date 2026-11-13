#!/usr/bin/env python3
"""Read-only readiness check; no solver invocation or data mutation."""
import csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'experiments/manifests/BASELINE_SHA256.json').read_text(encoding='utf-8'))
problems=[]
for rel,expected in manifest['files'].items():
 p=ROOT/rel
 if not p.is_file(): problems.append('MISSING '+rel);continue
 actual=hashlib.sha256(p.read_bytes()).hexdigest()
 if actual!=expected:problems.append('HASH_MISMATCH '+rel)
scenarios={'E100':100,'E200':200,'E300':300,'E375':375,'E450':450}
summary=[]
for scenario,nvehicles in scenarios.items():
 p=ROOT/f'data/processed/annual_charging/D28_demanda_anual_{scenario}_15min.csv'
 count=0;energy=0.;peak=0.;bad=0
 with p.open(encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f):
   if int(row['interval_start_min'])!=count*15:bad+=1
   power=float(row['power_ac_kw']);energy+=float(row['energy_ac_kwh']);peak=max(peak,power);count+=1
 if count!=35040 or bad:problems.append(f'CURVE_INVALID {scenario} count={count} bad={bad}')
 summary.append({'scenario':scenario,'vehicles':nvehicles,'intervals':count,'energy_ac_gwh':round(energy/1e6,6),'peak_ac_kw':round(peak,3)})
print(json.dumps({'baseline_hashes_checked':len(manifest['files']),'baseline_errors':problems,'curves':summary,'pcc_kw':2500,'solar_alignment':'NOT_APPROVED','scientific_optimization':'BLOCKED','solver_executions':0},ensure_ascii=False,indent=2))
if problems:sys.exit(1)
print('BASELINE_INTEGRITY_OK | SCIENTIFIC_RELEASE_BLOCKED')
