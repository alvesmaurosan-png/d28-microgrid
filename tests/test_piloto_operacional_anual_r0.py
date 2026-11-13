import importlib.util
from pathlib import Path

def test_pilot_preflight_module():
    path=Path(__file__).resolve().parents[1]/'scripts/executar_piloto_anual_r0.py'
    spec=importlib.util.spec_from_file_location('d28_annual_pilot',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert set(module.VALIDATORS)=={'A','B','C'}
    assert module.INPUT.name=='R0_inputs_E100_15min.csv'
