from pathlib import Path
import ast
from d28.validation.objective_gate import objective_triplet
from d28.validation.charging_sessions import validate_sessions

def test_objectives():
    assert objective_triplet(0.3,500,0.02)==(0.3,500.,0.02)

def test_sessions_present_and_checked():
    root=Path(__file__).resolve().parents[1]
    result=validate_sessions(root/'data/raw/logistics/sessoes_conciliadas_115.csv')
    assert result['sessions']>0
    assert result['full_fleet_homologated'] is False

def test_four_architecture_sources_parse():
    root=Path(__file__).resolve().parents[1]
    for rel in ['src/d28/dispatch/milp.py','src/d28/dispatch/r1.py',
                'src/d28/dispatch/r2_r3.py','src/d28/dispatch/individual_charging.py',
                'src/d28/optimization/architecture_evaluator.py']:
        ast.parse((root/rel).read_text(encoding='utf-8-sig'))
