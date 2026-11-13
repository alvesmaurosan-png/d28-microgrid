import importlib.util
from pathlib import Path

script = Path(__file__).resolve().parents[1] / 'scripts/reconciliar_f3_rev081e.py'
spec = importlib.util.spec_from_file_location('rev081e', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_classification():
    assert module.classify('MISSING_FACTOR:D11-014')[0] == 'FATORES_DE_EMISSAO'
    assert module.classify('MISSING_ACTIVITY:annual_fuel_nm3')[0] == 'DADOS_DE_ATIVIDADE'
    assert module.classify('MISSING_LCA_BOUNDARY:END_OF_LIFE')[0] == 'FRONTEIRAS_ACV'
    assert module.classify('PKM_SYNTHETIC_NOT_HOMOLOGATED')[0] == 'CRITERIOS_CONTABILIZACAO'


def test_no_loss_and_deduplication():
    source = {'revision': 'REV08.1d', 'reports': {a: {'blockers': ['MISSING_FACTOR:D11-014',
              'MISSING_LCA_BOUNDARY:END_OF_LIFE']} for a in ('R0', 'R1', 'R2', 'R3')}}
    result = module.reconcile(source)
    assert result['total_original_records'] == 8
    assert result['unique_root_causes'] == 2
    assert sum(x['occurrences'] for x in result['root_causes']) == 8
    assert result['f3_complete'] is False
