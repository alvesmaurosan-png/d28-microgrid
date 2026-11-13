"""REV05.2: dimensionamento condicionado do R2, sem aprovação científica.

Produção exógena derivada de vazão assumida de substrato. Não há dinâmica
biológica ou escolha endógena de substrato/volume no MILP.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
from d28.traceability.base_master import load_base_master

REQUIRED = {
 'D08-002':'fração','D08-003':'Nm³ CH4/t substrato úmido',
 'D08-005':'dias','D08-006':'fração','D08-007':'t/m³',
 'D08-013':'fração geração CHP','D09-003':'fração Pnom',
 'D09-011':'horas',
}

def conditional_r2_sizing(base_path, *, substrate_t_per_day, chp_capacity_kw,
                          electrical_efficiency, fuel_lhv_kwh_per_nm3,
                          dt_hours, intervals, initial_stock_fraction=0.5):
    """Retorna entradas físicas compatíveis com build_r2_milp e trilha de auditoria."""
    recs={r['id']:r for r in load_base_master(base_path)}
    vals={}; audit=[]
    for id_, unit in REQUIRED.items():
        r=recs[id_]
        if r['unit']!=unit:raise ValueError(f'{id_}: unidade inesperada {r["unit"]!r}')
        try:v=float(r['value_raw'])
        except (TypeError,ValueError) as exc:raise ValueError(f'{id_}: valor inválido') from exc
        if not math.isfinite(v) or v<=0:raise ValueError(f'{id_}: valor fora do domínio')
        vals[id_]=v
        audit.append({'id':id_,'value':v,'unit':unit,'source_reference':r['source_reference'],
                      'evidence_status':r['evidence_status'],'approval':'NOT_HOMOLOGATED'})
    for name,v in [('substrate_t_per_day',substrate_t_per_day),('chp_capacity_kw',chp_capacity_kw),
                   ('electrical_efficiency',electrical_efficiency),('fuel_lhv_kwh_per_nm3',fuel_lhv_kwh_per_nm3),
                   ('dt_hours',dt_hours),('initial_stock_fraction',initial_stock_fraction)]:
        if not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
            raise ValueError(f'{name}: valor inválido')
    if not isinstance(intervals,int) or intervals<=0:raise ValueError('intervals inválido')
    if not 0<initial_stock_fraction<=1 or not 0<electrical_efficiency<=1:raise ValueError('fração inválida')
    if not (0<vals['D08-002']<=1 and 0<vals['D08-006']<=1 and 0<vals['D08-013']<1
            and 0<vals['D09-003']<=1):raise ValueError('frações da Base Mestre inválidas')
    # D08-003: CH4 Nm3/t; dividir por fração CH4 para obter biogás bruto Nm3/t.
    biogas_nm3_day=substrate_t_per_day*vals['D08-003']/vals['D08-002']
    # D08-007 densidade t/m3; TRH em dias; fração útil do volume geométrico.
    digester_m3=substrate_t_per_day/vals['D08-007']*vals['D08-005']/vals['D08-006']
    rated_fuel_nm3_h=chp_capacity_kw/(electrical_efficiency*fuel_lhv_kwh_per_nm3)
    gasometer_nm3=rated_fuel_nm3_h*vals['D09-011']
    biogas_nm3_interval=biogas_nm3_day*dt_hours/24.0
    config={'production_nm3':[biogas_nm3_interval]*intervals,
            'gasometer_capacity_nm3':gasometer_nm3,
            'initial_gas_nm3':initial_stock_fraction*gasometer_nm3,
            'terminal_gas_policy':'cyclic',
            'auxiliary_fraction_chp_gross':vals['D08-013'],
            'minimum_load_fraction':vals['D09-003'],
            'digester_capacity_m3':digester_m3,
            'substrate_t_per_day':substrate_t_per_day,
            'physical_evidence':{
              'biogas_yield_nm3_per_t':vals['D08-003']/vals['D08-002'],
              'substrate_density_t_per_m3':vals['D08-007'],
              'hydraulic_retention_days':vals['D08-005'],
              'usable_volume_fraction':vals['D08-006'],
              'gasometer_autonomy_hours':vals['D09-011']}}
    return {'biogas':config,'chp_minimum_load_fraction':vals['D09-003'],
            'derived':{'biogas_nm3_per_day':biogas_nm3_day,
                       'biogas_nm3_per_interval':biogas_nm3_interval,
                       'digester_geometric_m3':digester_m3,
                       'gasometer_capacity_nm3':gasometer_nm3,
                       'chp_rated_fuel_nm3_per_hour':rated_fuel_nm3_h},
            'audit':{'base_master_sha256':hashlib.sha256(Path(base_path).read_bytes()).hexdigest(),
                     'records':audit,'experimental_assumptions':{
                     'substrate_t_per_day':substrate_t_per_day,
                     'initial_stock_fraction':initial_stock_fraction,
                     'substrate_supply':'ASSUMED_GUARANTEED_NOT_DOCUMENTED',
                     'biogas_production':'CONSTANT_EXOGENOUS_DERIVED_NOT_BIOLOGICAL_DYNAMICS',
                     'gasometer_autonomy':'AT_CHP_RATED_FUEL_FLOW',
                     'auxiliary':'FRACTION_OF_CHP_GROSS_NOT_ADDED_TO_REV09_SOURCE',
                     'substrate_and_gas_composition':'CONSTANT',
                     'gas_stock_loss':'NONNEGATIVE_CURTAILMENT_NO_LEAKAGE_MODEL'},
                     'scientific_approval':False,'annualization':'BLOCKED','nsga2':'BLOCKED'}}
