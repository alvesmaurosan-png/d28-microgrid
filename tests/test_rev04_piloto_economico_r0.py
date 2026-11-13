"""Testes unitarios de invariantes da REV04; nao iniciam simulacao anual."""
import importlib.util
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'04_piloto_economico_r0.py'
spec=importlib.util.spec_from_file_location('rev04_piloto',SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_tariff_shape():
    assert len(module.LOAD)==len(module.PV_PU)==len(module.TARIFF)==4
    assert all(t>=0 for t in module.TARIFF)

def test_one_hour_only():
    assert len(module.LOAD)*module.DT==1.

def test_invalid_margin_rejected():
    import pytest
    with pytest.raises(ValueError):
        module.run(-1)
