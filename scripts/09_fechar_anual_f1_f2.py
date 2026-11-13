"""Executa auditoria final; nunca aprova evidência automaticamente."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    contract=json.loads((ROOT/'contrato_anual.json').read_text(encoding='utf-8-sig'))
    report_path=ROOT/'results/REV09_FECHAMENTO_AUDITORIA.json'
    if not report_path.exists():
        print('REV09_REPORT_MISSING: copie results/ do pacote')
        return 2
    report=json.loads(report_path.read_text(encoding='utf-8'))
    print('REV09 SCIENTIFIC RELEASE:', 'BLOCKED' if contract.get('status')!='APPROVED' else 'REQUIRES_REAUDIT')
    print('ANNUAL MILP EXECUTED:',report['annual_milp_executed'])
    print('F1/F2 ANNUAL VERIFIED:',report['f1_f2_verified'])
    print('PENDING:', ', '.join(report['blocking_ids']))
    return 0
if __name__=='__main__':raise SystemExit(main())
