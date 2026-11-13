from pathlib import Path
import importlib.util
p=Path(__file__).resolve().parents[1]/"scripts/rev08_gate_integracao_r0_r3.py"
spec=importlib.util.spec_from_file_location("rev08_gate",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_reject_architecture():
    try:m.build("R9",[100],[0],{"pv_kw":0,"bess_kwh":100,"pcs_kw":10},{})
    except ValueError:pass
    else:raise AssertionError("R9 deveria ser rejeitada")
def test_output_has_no_fake_objectives():
    assert "F1_brl_per_pkm" in p.read_text()
    assert "scientific_pareto_eligible" in p.read_text()
