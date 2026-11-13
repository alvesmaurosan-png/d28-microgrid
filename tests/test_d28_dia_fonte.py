import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/validar_d28_dia_fonte_r0_r3.py'
spec = importlib.util.spec_from_file_location('validar_d28_dia_fonte', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_real_source_day_has_96_intervals():
    load, solar, status = mod.source_day('E100', 0)
    assert len(load) == len(solar) == 96
    assert all(x >= 0 for x in load + solar)
    assert status


def test_sources_are_fingerprinted():
    assert len(mod.sha256(mod.DEMAND)) == 64
    assert len(mod.sha256(mod.SOLAR)) == 64


def test_contract_not_approved():
    import json
    assert json.loads(mod.CONTRACT.read_text(encoding='utf-8-sig'))['status'] != 'APPROVED'
