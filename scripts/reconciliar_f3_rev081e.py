"""REV08.1e: reconcilia bloqueios REV08.1d sem alterar o avaliador físico/econômico."""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reports/D28_REV08_1D_F3_POR_ARQUITETURA.json'
TARGET = ROOT / 'reports/D28_REV08_1E_RECONCILIACAO_F3.json'


def classify(blocker):
    if blocker.startswith('MISSING_FACTOR:'):
        return 'FATORES_DE_EMISSAO', blocker.split(':', 1)[1]
    if blocker.startswith('MISSING_ACTIVITY:'):
        return 'DADOS_DE_ATIVIDADE', blocker.split(':', 1)[1]
    if blocker.startswith('MISSING_LCA_BOUNDARY:'):
        return 'FRONTEIRAS_ACV', blocker.split(':', 1)[1]
    if blocker.startswith(('PKM_', 'MISSING_OR_UNVERIFIED:', 'CGOB_')):
        return 'CRITERIOS_CONTABILIZACAO', blocker
    return 'NAO_CLASSIFICADO', blocker


def reconcile(source):
    reports = source['reports']
    by_arch = {}
    roots = defaultdict(lambda: {'architectures': set(), 'original_blockers': []})
    total = 0
    for arch in ('R0', 'R1', 'R2', 'R3'):
        blockers = reports[arch]['blockers']
        total += len(blockers)
        groups = defaultdict(list)
        for blocker in blockers:
            group, cause = classify(blocker)
            groups[group].append(blocker)
            key = (group, cause)
            roots[key]['architectures'].add(arch)
            roots[key]['original_blockers'].append({'architecture': arch, 'blocker': blocker})
        by_arch[arch] = {'original_count': len(blockers), 'counts_by_cause':
                         {k: len(v) for k, v in sorted(groups.items())},
                         'blockers_by_cause': dict(sorted(groups.items()))}
    root_list = [{'category': cat, 'root_cause': cause,
                  'architectures': sorted(entry['architectures']),
                  'occurrences': len(entry['original_blockers']),
                  'trace': entry['original_blockers']}
                 for (cat, cause), entry in sorted(roots.items())]
    return {'revision': 'REV08.1e', 'source_revision': source.get('revision'),
            'status': 'BLOCKER_RECONCILIATION_ONLY',
            'total_original_records': total, 'unique_root_causes': len(root_list),
            'by_architecture': by_arch, 'root_causes': root_list,
            'physical_models_modified': False, 'economics_modified': False,
            'f3_complete': False,
            'r3_rule': 'NATURAL_GAS_PHYSICAL; CGOB_ACCOUNTING_ONLY; NO_AUTOMATIC_EMISSION_DEDUCTION'}


def main():
    if not SOURCE.exists():
        raise SystemExit('Execute primeiro: python .\\scripts\\auditar_f3_rev081d.py')
    data = reconcile(json.loads(SOURCE.read_text(encoding='utf-8')))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('REV08.1e | registros:', data['total_original_records'], '| causas-raiz:', data['unique_root_causes'])
    for arch, result in data['by_architecture'].items():
        print(arch, result['original_count'], result['counts_by_cause'])
    print('F3 completo:', data['f3_complete'], '| relatório:', TARGET)


if __name__ == '__main__':
    main()
