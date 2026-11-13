"""Exporta parâmetros existentes e lacunas, sem inventar séries anuais."""
import csv, json, math
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'
OUT=ROOT/'reports/D28_ENTRADAS_F1_F3_RASTREAVEIS.json'

def prepare(base=BASE):
    wb=load_workbook(base,read_only=True,data_only=True)
    ws=wb['Parametros_137']; rows=ws.iter_rows(values_only=True); hdr=next(rows)
    items=[]
    for r in rows:
        if not r[0] or not str(r[0]).startswith('D'):continue
        v=r[3]
        if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v): kind='numeric'
        else: kind='non_numeric_or_unquantified'
        items.append({'id':str(r[0]),'name':str(r[2] or ''),'value':v,'unit':r[4], 'reference':r[5], 'source_url':r[6], 'f1_flag':r[8] if len(r)>8 else None,'value_type':kind})
    result={'source':str(base.relative_to(ROOT)) if base.is_relative_to(ROOT) else str(base),
      'parameters':items,'parameter_count':len(items),
      'annual_cashflows_brl':None,'annual_pkm':None,'lifecycle_ghg_components_kgco2e':None,
      'F1':'NOT_COMPUTED_NO_DOCUMENTED_20_YEAR_INPUTS',
      'F3':'NOT_COMPUTED_NO_COMPLETE_LCA_AND_PKM',
      'interpretation':'numeric values are source records, not approvals; no annualization'}
    return result

if __name__=='__main__':
    data=prepare();OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(f'Exportados {data["parameter_count"]} parâmetros da Base Mestre -> {OUT}')
    print('F1/F3 não calculados: séries anuais e inventário ACV não demonstrados.')
