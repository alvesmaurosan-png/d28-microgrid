"""Produce non-destructive ID -> source -> model symbol audit, without approval."""
import csv
import json
from pathlib import Path
from d28.traceability.base_master import build_report

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'
OUT = ROOT / 'reports'
OUT.mkdir(exist_ok=True)
report = build_report(SOURCE)
json_path = OUT / 'D28_REV05_RASTREABILIDADE_137_IDS.json'
json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
csv_path = OUT / 'D28_REV05_VINCULOS_BASE_MESTRE.csv'
with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=report['records'][0].keys(), delimiter=';')
    writer.writeheader()
    writer.writerows(report['records'])
print(json.dumps({k:v for k,v in report.items() if k != 'records'}, ensure_ascii=False, indent=2))
print(f'Matriz: {csv_path}\nRelatório: {json_path}')
