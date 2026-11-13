from pathlib import Path
import pytest
from d28.traceability.r2_closure import validate_r2_inputs, verify_rev09_charging_boundary
ROOT=Path(__file__).resolve().parents[1]

def valid(**updates):
    a=dict(production_nm3=[10.]*96,substrate_t_per_day=10.,digester_capacity_m3=375.,
           gasometer_capacity_nm3=228.57142857142858,chp_capacity_kw=60.,
           electrical_efficiency=.35,fuel_lhv_kwh_per_nm3=6.,dt_hours=.25,
           physical_evidence={'biogas_yield_nm3_per_t':96.,'substrate_density_t_per_m3':1.,
              'hydraulic_retention_days':30.,'usable_volume_fraction':.8,
              'gasometer_autonomy_hours':8.})
    a.update(updates)
    return validate_r2_inputs(**a)

def test_valid_dimensions():
    result=valid()
    assert result['digester_minimum_m3']==375.
    assert result['scientific_approval'] is False

def test_inconsistent_production_rejected():
    with pytest.raises(ValueError,match='produção'): valid(production_nm3=[9.]*96)

def test_undersized_digester_rejected():
    with pytest.raises(ValueError,match='volume geométrico'): valid(digester_capacity_m3=374.)

def test_undersized_gasometer_rejected():
    with pytest.raises(ValueError,match='gasômetro'): valid(gasometer_capacity_nm3=100.)

def test_missing_evidence_rejected():
    with pytest.raises(ValueError,match='evidência'): valid(physical_evidence=None)

def test_rev09_boundary_is_not_overclaimed():
    r=verify_rev09_charging_boundary(ROOT/'data/raw/demanda/D28_REV09_demanda_15min.csv',
                                    ROOT/'scripts/gerar_calendario_anual.py')
    assert r['generator_declares_charging_only'] is True
    assert r['csv_lineage_to_generator'].startswith('NOT_DEMONSTRATED')
    assert r['scientific_approval'] is False
