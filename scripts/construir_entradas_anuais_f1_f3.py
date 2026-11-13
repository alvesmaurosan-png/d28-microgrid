"""Build traceable annual input contracts; no extrapolation of daily dispatch.
Usage: python scripts/construir_entradas_anuais_f1_f3.py
"""
from __future__ import annotations
import json, math, hashlib
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'
MANIFEST=ROOT/'data/processed/annual_charging/manifesto_anual.json'
OUT=ROOT/'reports/D28_CONTRATOS_ANUAIS_F1_F3_RASTREAVEIS.json'

def _hash(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def _records(path):
    wb=load_workbook(path,read_only=True,data_only=True)
    ws=wb['Parametros_137']; headers=next(ws.values)
    out={}
    for r in ws.values:
        if not r or not isinstance(r[0],str) or not r[0].startswith('D'):continue
        out[r[0]]={'id':r[0],'name':r[2], 'raw_value':r[3], 'unit':r[4],
          'reference':r[5], 'evidence_status':r[16] if len(r)>16 else None,
          'decision':r[15] if len(r)>15 else None,
          'source_original':r[24] if len(r)>24 else None}
    return out

def _numeric(r):
    if r is None or isinstance(r['raw_value'],bool):return None
    try:v=float(r['raw_value'])
    except (ValueError,TypeError):return None
    return v if math.isfinite(v) else None

def build(base=BASE,manifest=MANIFEST):
    rec=_records(base)
    data=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else None
    scenarios={}
    if data:
        for s in data.get('summaries',[]):
            name=s['scenario']
            scenarios[name]={
              'energy_ac_kwh_2025_synthetic':s.get('energy_ac_kwh'),
              'peak_ac_kw_2025_synthetic':s.get('peak_ac_kw'),
              'intervals':s.get('intervals'),
              'source':'data/processed/annual_charging/manifesto_anual.json',
              'evidence':'ANNUAL_SYNTHETIC_GENERATED_NOT_HOMOLOGATED',
              'use_for_F1_F3':'REFERENCE_ONLY_NOT_ANNUAL_R0_R3_DISPATCH'}
    trace={}
    for id_,r in rec.items():
        trace[id_]={**r,'numeric_value':_numeric(r),'numeric_is_approved':False,
                    'source_file':'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'}
    tariff_ids=['D05-003','D05-004']
    tariff={k:trace.get(k) for k in tariff_ids}
    years=[]
    for y in range(1,21):
        years.append({'year_index':y,'calendar_year':None,'scenario':None,
          'annual_pkm':None,'annual_grid_import_kwh_by_architecture':{k:None for k in ('R0','R1','R2','R3')},
          'monthly_pcc_peaks_kw_by_architecture':{k:None for k in ('R0','R1','R2','R3')},
          'annual_fuel_by_architecture':{k:None for k in ('R0','R1','R2','R3')},
          'cashflow_brl2026_by_architecture':{k:None for k in ('R0','R1','R2','R3')},
          'operational_ghg_kgco2e_by_architecture':{k:None for k in ('R0','R1','R2','R3')},
          'evidence_status':'NOT_CONNECTED_TO_APPROVED_ANNUAL_DISPATCH'})
    missing=[
      {'code':'M01','field':'scenario_year_map','why':'approved mapping of E100/E200/E300/E375/E450 to 20 calendar years','blocks':['F1','F3']},
      {'code':'M02','field':'annual_dispatch_R0_R3','why':'20-year annual imports, monthly peaks, fuels and asset operation; daily 96-interval outputs cannot be scaled silently','blocks':['F1','F3']},
      {'code':'M03','field':'annual_pkm','why':'passenger-km per year and documented service boundary','blocks':['F1','F3']},
      {'code':'M04','field':'economic_contract','why':'approved CAPEX, OPEX, tariffs, replacements, residual value and escalation/discount treatment per architecture','blocks':['F1']},
      {'code':'M05','field':'LCA_factors','why':'traceable quantified factors D11-014/015/016/018/019 and complete disjoint life-cycle inventory','blocks':['F3']},
      {'code':'M06','field':'LCA_boundary','why':'documented separation of assets, replacements, operation, upstream, fugitive, end-of-life and credits','blocks':['F3']}
    ]
    return {'schema':'D28_ANNUAL_F1_F3_CONTRACT_V1','status':'INPUT_CONTRACT_PARTIALLY_POPULATED',
      'source_hashes_sha256':{'base_master':_hash(base),'annual_manifest':_hash(manifest) if manifest.exists() else None},
      'f1_equation':'PC-REV08 EQ-040','f3_equation':'PC-REV08 EQ-045',
      'discount_rate_from_implemented_objective':0.12,'years':years,
      'annual_synthetic_reference_scenarios':scenarios,'tariff_parameter_records':tariff,
      'parameter_registry':trace,'parameter_count':len(trace),
      'lca_required_factor_records':{k:trace.get(k) for k in ('D11-014','D11-015','D11-016','D11-018','D11-019')},
      'blocking_gaps':missing,'F1':None,'F3':None,
      'rules':['Source numeric value is not automatically homologated',
               'Synthetic charging year is not optimized annual grid import',
               'No extrapolation from a single day',
               'No zero substituted for missing emissions',
               'No changes to R0-R3 dispatch']}

if __name__=='__main__':
    result=build();OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(f'Parâmetros: {result["parameter_count"]}; cenários anuais de referência: {len(result["annual_synthetic_reference_scenarios"])}; anos estruturados: {len(result["years"])}')
    print('Lacunas impeditivas:',', '.join(x['code'] for x in result['blocking_gaps']))
    print('Relatório:',OUT)
