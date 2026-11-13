import pytest
from d28.dispatch.individual_charging import attach_individual_charging

def test_rev09_nao_duplicar():
    with pytest.raises(ValueError,match='não admite'):
        attach_individual_charging(object(),mode='aggregated_rev09',sessions=[{'session_id':'s1'}])

def test_rev09_puro():
    obj=object()
    assert attach_individual_charging(obj,mode='aggregated_rev09') is obj
