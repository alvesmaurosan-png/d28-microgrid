"""Preenche somente evidências anuais demonstráveis; preserva o contrato V1 e o despacho."""
from pathlib import Path
import json, hashlib, math
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'reports/D28_CONTRATOS_ANUAIS_F1_F3_RASTREAVEIS.json'
OUT=ROOT/'reports/D28_CONTRATOS_ANUAIS_F1_F3_INTEGRADOS_REV01.json'
CONFIG=ROOT/'config/economics/r0_f1_exploratory_2026.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def finite(v):
    if isinstance(v,bool):return None
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None

def integrate(data, config=None):
    """No assumption of annual R0-R3 dispatch, approved year map or approved LCA."""
    d=json.loads(json.dumps(data))
    p=d['parameter_registry']
    def record(id):
        r=p.get(id)
        if not r: return None
        v=finite(r.get('raw_value'))
        if v is None:return None
        return {'value':v,'unit':r.get('unit'),'parameter_id':id,'source_file':r.get('source_file'),
                'evidence_status':r.get('evidence_status'),'approval':'NOT_INFERRED'}
    d['integrated_parameter_values']={k:v for k in p if (v:=record(k)) is not None}
    # The annual calendar and distance are documented assumptions, not observed vehicle activity.
    ids=['D04-001','D04-002','D04-003','D04-004','D04-005','D04-006','D04-007']
    vals=[record(k) for k in ids]
    if all(v is not None for v in vals):
        km=sum(vals[i]['value']*vals[i+3]['value'] for i in range(3))
        days=sum(vals[i]['value'] for i in (3,4,5))
        pkm=km*vals[6]['value']
        d['service_reference']={'km_per_bus_year_conditional':km,
          'pkm_per_bus_year_conditional':pkm,'calendar_days':days,
          'parameter_ids':ids,'status':'CONDITIONAL_FROM_MASTER_NOT_APPROVED_ANNUAL_PKM',
          'assumption':'one bus operates each specified day at reference km and occupancy; no service-availability correction'}
    else:
        d['service_reference']=None
    for name,s in d['annual_synthetic_reference_scenarios'].items():
        s['vehicles']=int(name[1:]) if name[1:].isdigit() else None
        if d['service_reference'] and s['vehicles'] is not None:
            s['annual_pkm_reference_conditional']=d['service_reference']['pkm_per_bus_year_conditional']*s['vehicles']
            s['annual_km_reference_conditional']=d['service_reference']['km_per_bus_year_conditional']*s['vehicles']
        else:
            s['annual_pkm_reference_conditional']=None
            s['annual_km_reference_conditional']=None
        s['annual_charging_energy_ac_kwh']=s.get('energy_ac_kwh_2025_synthetic')
        s['annual_charging_peak_ac_kw']=s.get('peak_ac_kw_2025_synthetic')
        s['annual_grid_import_kwh_R0_R3']=None
        s['note']='Charging-only AC; not grid import, no base load, PV, BESS, CHP or monthly PCC peaks.'
    # Source-backed financial assumptions; not automatically approved for F1.
    economics=['D05-003','D05-004','D06-006','D06-007','D06-008','D07-013','D07-014',
               'D07-015','D07-016','D07-017','D08-008','D08-009','D08-010','D08-011',
               'D08-012','D09-006','D09-007','D09-008','D09-009','D09-010','D09-012',
               'D09-013','D09-014','D10-002','D10-003','D10-004','D10-005','D10-006','D10-007']
    d['economic_parameter_inputs']={k:record(k) for k in economics}
    environment=['D11-%03d'%i for i in range(2,20)]
    d['environmental_parameter_inputs']={k:record(k) for k in environment}
    d['exploratory_economic_config']=config if config else None
    # Annual rows intentionally retain unknown calendar/scenario and dispatch values.
    for y in d['years']:
        y['discount_factor_conditional']=(1+record('D10-003')['value'])**(-y['year_index']) if record('D10-003') else None
        y['discount_factor_parameter_id']='D10-003' if record('D10-003') else None
        y['annual_pkm']=None
    d['integration_revision']='REV01_EVIDENCE_ONLY'
    d['status']='PARTIALLY_POPULATED_NO_NUMERIC_F1_F3'
    d['integrated_evidence']={'annual_synthetic_charging':'POPULATED_REFERENCE_ONLY',
      'conditional_service_pkm':'POPULATED_REFERENCE_ONLY' if d['service_reference'] else 'MISSING',
      'numeric_economic_parameters':'POPULATED_NOT_AUTOMATICALLY_APPROVED',
      'numeric_environmental_parameters':'POPULATED_NOT_AUTOMATICALLY_APPROVED',
      'annual_optimized_dispatch':'MISSING','annual_approved_pkm':'MISSING',
      'complete_LCA':'MISSING'}
    return d

def main():
    if not SOURCE.exists():raise SystemExit('Execute antes construir_entradas_anuais_f1_f3.py')
    d=json.loads(SOURCE.read_text(encoding='utf-8'))
    cfg=json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else None
    result=integrate(d,cfg)
    result['integration_source_sha256']={'contract_v1':sha(SOURCE),'economic_config':sha(CONFIG) if CONFIG.exists() else None}
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
    print('Parâmetros numéricos rastreados:',len(result['integrated_parameter_values']))
    print('PKM condicional por ônibus/ano:',result['service_reference']['pkm_per_bus_year_conditional'] if result['service_reference'] else None)
    print('Cenários anuais:',len(result['annual_synthetic_reference_scenarios']))
    print('F1/F3:',result['F1'],result['F3'])
    print('Relatório:',OUT)
if __name__=='__main__':main()
