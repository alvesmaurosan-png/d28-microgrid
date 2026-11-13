from pathlib import Path
import pytest
from d28.traceability.base_master import BINDINGS, build_report, controlled_values, load_base_master

SOURCE = Path(__file__).resolve().parents[1] / 'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'

def test_137_ids_unique_and_source_hashed():
    report = build_report(SOURCE)
    assert report['record_count'] == 137
    assert len(report['sha256']) == 64
    assert report['approved_for_execution_count'] == 0

def test_explicit_bindings_are_grounded_in_base():
    records = load_base_master(SOURCE)
    by_id = {r['id']:r for r in records}
    assert set(BINDINGS) <= set(by_id)
    assert by_id['D05-001']['model_symbol'] == 'dispatch.pcc_import_limit_kw'
    assert by_id['D05-001']['value_raw'] == '2500'
    assert by_id['D11-015']['missing_lca_factor'] is True

def test_no_implicit_parameter_approval():
    records = load_base_master(SOURCE)
    assert controlled_values(records) == {}
    assert all(r['usage'] != 'APPROVED' for r in records)

def test_explicit_approval_only_and_invalid_rejected():
    records = load_base_master(SOURCE)
    out = controlled_values(records, approved_ids=['D05-001'])
    assert out['dispatch.pcc_import_limit_kw']['value'] == 2500
    with pytest.raises(ValueError):
        controlled_values(records, approved_ids=['D11-015'])
    with pytest.raises(ValueError):
        controlled_values(records, approved_ids=['D99-999'])
