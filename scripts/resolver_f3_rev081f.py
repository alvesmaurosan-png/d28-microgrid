"""REV08.1f: resolução conservadora de 23 causas-raiz sem alterar modelos."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'reports/D28_REV08_1E_RECONCILIACAO_F3.json'
AUDIT = ROOT / 'reports/D28_REV08_1D_F3_POR_ARQUITETURA.json'
OUTPUT = ROOT / 'reports/D28_REV08_1F_RESOLUCAO_CAUSAS_F3.json'


def finite_nonnegative(value):
    try:
        import math
        return value is not None and not isinstance(value, bool) and math.isfinite(float(value)) and float(value) >= 0
    except (TypeError, ValueError):
        return False


def resolve(reconciled, audited):
    reports = audited['reports']
    outcomes = []
    for root in reconciled['root_causes']:
        category = root['category']
        cause = root['root_cause']
        decisions = []
        for arch in root['architectures']:
            record = reports[arch]
            state = 'PENDENTE'
            evidence = []
            note = 'Sem evidência suficiente para encerrar esta causa.'
            if category == 'FATORES_DE_EMISSAO':
                factor = record.get('factors', {}).get(cause)
                if factor and finite_nonnegative(factor.get('value')):
                    state = 'RESOLVIDA'
                    evidence = ['REV08.1d:factors:' + arch + ':' + cause]
                    note = 'Fator numérico existente; homologação científica não presumida.'
                else:
                    note = 'Fator ausente ou inválido na Base Mestre conforme auditoria REV08.1d.'
            elif category == 'DADOS_DE_ATIVIDADE':
                components = [c for bucket in record.get('partial_components', {}).values()
                              for c in bucket if c.get('component') == cause and finite_nonnegative(c.get('activity'))]
                if components:
                    state = 'RESOLVIDA'
                    evidence = ['REV08.1d:partial_components:' + arch + ':' + cause]
                    note = 'Atividade documentada no relatório; não implica ACV completa.'
                else:
                    note = 'Atividade anual específica não demonstrada na auditoria; não reutilizar dados R0 para R1-R3.'
            elif category == 'CRITERIOS_CONTABILIZACAO':
                if cause == 'PKM_SYNTHETIC_NOT_HOMOLOGATED':
                    evidence = ['REV08.1c:PKM_sintetico_E100_137675700']
                    note = 'PKM calculado sob hipótese sintética, ainda sem homologação.'
                elif cause.startswith('CGOB_'):
                    note = 'CGOB não substitui combustível físico; verificar cobertura apenas com consumo de gás demonstrado.'
                else:
                    note = 'Critério de normalização ou contabilização sem validação documental.'
            elif category == 'FRONTEIRAS_ACV':
                note = 'Cobertura da fronteira não comprovada; componentes parciais não encerram inventário.'
            decisions.append({'architecture': arch, 'status': state, 'evidence': evidence, 'note': note})
        outcomes.append({'category': category, 'root_cause': cause,
                         'occurrences': root['occurrences'], 'decisions': decisions,
                         'root_status': 'RESOLVIDA' if all(x['status'] == 'RESOLVIDA' for x in decisions)
                                        else 'NAO_APLICAVEL' if all(x['status'] == 'NAO_APLICAVEL' for x in decisions)
                                        else 'PENDENTE'})
    if sum(x['occurrences'] for x in outcomes) != reconciled['total_original_records']:
        raise ValueError('Perda de rastreabilidade entre revisões')
    if len(outcomes) != reconciled['unique_root_causes']:
        raise ValueError('Número de causas-raiz inconsistente')
    statuses = {s: sum(x['root_status'] == s for x in outcomes)
                for s in ('RESOLVIDA', 'NAO_APLICAVEL', 'PENDENTE')}
    return {'revision': 'REV08.1f', 'source': 'REV08.1e + REV08.1d',
            'original_records': reconciled['total_original_records'],
            'unique_root_causes': len(outcomes), 'root_status_counts': statuses,
            'roots': outcomes, 'f3_complete': False,
            'r3_policy': 'NATURAL_GAS_PHYSICAL_CGOB_ACCOUNTING_ONLY_NO_AUTO_DEDUCTION',
            'physical_models_modified': False, 'economic_models_modified': False,
            'scope': 'ONLY_EXPLICIT_EVIDENCE_IN_EXISTING_AUDIT; NO_INFERRED_ACTIVITIES'}


def main():
    for path in (INPUT, AUDIT):
        if not path.exists():
            raise SystemExit('Arquivo não encontrado: ' + str(path))
    rec = json.loads(INPUT.read_text(encoding='utf-8'))
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    result = resolve(rec, audit)
    result['input_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (INPUT, AUDIT)}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('REV08.1f | causas:', result['unique_root_causes'], '| registros:', result['original_records'])
    print('Classificação:', result['root_status_counts'])
    print('F3 completo:', result['f3_complete'], '| relatório:', OUTPUT)


if __name__ == '__main__':
    main()
