import pytest
from d28.optimization.architecture_evaluator import Evaluation,nsga2_adapter,evaluate_architecture

def test_bloqueio_f3():
    assert not evaluate_architecture('R0',object(),solve=lambda m: {'optimal':True},
        compute_f1=lambda *a: 1,compute_f3=None,annual_pkm=100,life_years=10).feasible

def test_nsga2_rejeita_incompletos():
    with pytest.raises(ValueError):nsga2_adapter([Evaluation(False,None,'faltando F3',{})])

def test_nsga2_formato():
    assert nsga2_adapter([Evaluation(True,(1,2,3),'',{})])==[[1,2,3]]
