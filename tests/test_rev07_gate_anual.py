import importlib.util
from pathlib import Path
MODULE=Path(__file__).resolve().parents[1]/'scripts/07_auditar_liberacao_anual.py'
spec=importlib.util.spec_from_file_location('rev07_gate',MODULE)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def test_missing_contract_blocks(tmp_path):
    r=mod.audit(tmp_path)
    assert not r['scientific_release']
    assert r['f3_excluded']
def test_pending_contract_blocks(tmp_path):
    (tmp_path/'contrato_anual.json').write_text('{"status":"PENDING_RESEARCHER_APPROVAL","year":2025}',encoding='utf-8')
    r=mod.audit(tmp_path)
    assert not r['scientific_release']
    assert not next(x for x in r['checks'] if x['id']=='CONTRACT_APPROVED')['pass']
