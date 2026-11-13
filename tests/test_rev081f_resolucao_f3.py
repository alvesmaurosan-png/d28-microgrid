import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'scripts/resolver_f3_rev081f.py'
spec = importlib.util.spec_from_file_location('rev081f', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_factor_not_invented():
    rec = {'total_original_records': 1, 'unique_root_causes': 1,
           'root_causes': [{'category': 'FATORES_DE_EMISSAO', 'root_cause': 'D11-014',
                           'architectures': ['R0'], 'occurrences': 1}]}
    audit = {'reports': {'R0': {'factors': {'D11-014': {'value': None}}}}}
    result = module.resolve(rec, audit)
    assert result['root_status_counts']['PENDENTE'] == 1
    assert not result['f3_complete']


def test_present_factor_only_resolves_factor():
    rec = {'total_original_records': 1, 'unique_root_causes': 1,
           'root_causes': [{'category': 'FATORES_DE_EMISSAO', 'root_cause': 'D11-017',
                           'architectures': ['R0'], 'occurrences': 1}]}
    audit = {'reports': {'R0': {'factors': {'D11-017': {'value': 0.0996}}}}}
    assert module.resolve(rec, audit)['root_status_counts']['RESOLVIDA'] == 1


def test_r3_no_automatic_cgob_offset():
    rec = {'total_original_records': 1, 'unique_root_causes': 1,
           'root_causes': [{'category': 'CRITERIOS_CONTABILIZACAO',
                           'root_cause': 'CGOB_COVERAGE_EXCEEDS_PHYSICAL_NATURAL_GAS_CONSUMPTION',
                           'architectures': ['R3'], 'occurrences': 1}]}
    audit = {'reports': {'R3': {}}}
    result = module.resolve(rec, audit)
    assert result['root_status_counts']['PENDENTE'] == 1
    assert 'NO_AUTO_DEDUCTION' in result['r3_policy']
