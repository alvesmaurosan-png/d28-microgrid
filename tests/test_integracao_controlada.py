import pytest
from d28.validation.objective_gate import objective_triplet
def test_objetivos_completos():
    assert objective_triplet(.2,2500,.03)==(.2,2500.,.03)
def test_f3_ausente_bloqueia():
    with pytest.raises(ValueError):objective_triplet(.2,2500,None)
def test_valores_invalidos_bloqueiam():
    with pytest.raises(ValueError):objective_triplet(float("nan"),2500,.03)
