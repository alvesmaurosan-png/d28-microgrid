"""Calcula parcelas evidenciadas sem atribuí-las indevidamente a F1/F3 anuais R0-R3."""
from pathlib import Path
import json, math, hashlib

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'reports/D28_CONTRATOS_ANUAIS_F1_F3_INTEGRADOS_REV01.json'
OUT=ROOT/'reports/D28_PARCELAS_F1_F3_CALCULAVEIS_REV02.json'

def calc(d):
    reg=d['parameter_registry']
    def par(k):
        v=reg[k]; x=v.get('numeric_value')
        if x is None:
            try:x=float(str(v['raw_value']).replace(',','.'))
            except (ValueError,TypeError):return None
        x=float(x)
        if not math.isfinite(x):return None
        return {'value':x,'unit':v.get('unit'),'parameter_id':k,'source_file':v.get('source_file'),'evidence_status':v.get('evidence_status'),'numeric_is_approved':v.get('numeric_is_approved',False)}
    rate=par('D10-003'); years=par('D10-002')
    if rate is None or years is None or int(years['value'])!=20:raise ValueError('Horizonte/taxa indisponíveis')
    a=sum((1+rate['value'])**(-y) for y in range(1,21))
    factor=par('D11-017'); legacy=par('D11-002')
    service=d.get('service_reference') or {}
    perbus=service.get('pkm_per_bus_year_conditional')
    out={'revision':'REV02_PARCELAS_CALCULAVEIS','F1':None,'F3':None,
      'annualized_R0_R3':False,'physical_dispatch':'UNCHANGED',
      'discount':{'rate':rate,'horizon':years,'annuity_factor_20y_conditional':a},
      'parameterized_components':{},'synthetic_reference_scenarios':{},
      'blocking_for_final_objectives':{'F1':['annual_R0_R3_cashflows','annual_R0_R3_grid_import_and_monthly_peaks','approved_annual_PKM','design_capacities_and_replacements_per_architecture'],
        'F3':['annual_R0_R3_operational_inventory','approved_annual_PKM','missing_D11_014_015_016_018_019','documented_nonoverlapping_LCA_boundaries']}}
    for k in ('D10-004','D10-005','D10-006','D10-007','D11-003','D11-004','D11-005','D11-006','D11-007','D11-008','D11-009','D11-010','D11-011','D11-012','D11-013','D11-017','D11-002'):
        out['parameterized_components'][k]=par(k)
    for name,s in d['annual_synthetic_reference_scenarios'].items():
        energy=s.get('annual_charging_energy_ac_kwh')
        vehicles=s.get('vehicles')
        row={'status':'SYNTHETIC_CHARGING_ONLY_NOT_R0_R3_GRID_IMPORT',
             'annual_charging_ac_kwh':energy,
             'charging_source':s.get('source'),
             'annual_pkm_conditional':s.get('annual_pkm_reference_conditional'),
             'pkm_parameter_ids':service.get('parameter_ids'),
             'emissions_SIN_proxy_kgco2e':None,
             'emissions_SIN_proxy_factor':factor,
             'legacy_direct_SIN_proxy_kgco2':None,
             'legacy_factor':legacy,
             'grid_bill_brl':None,'full_F1':None,'full_F3':None}
        if energy is not None:
            if factor:row['emissions_SIN_proxy_kgco2e']=float(energy)*factor['value']
            if legacy:row['legacy_direct_SIN_proxy_kgco2']=float(energy)*legacy['value']
        if vehicles is not None and perbus is not None:
            row['conditional_20y_pkm_undiscounted']=vehicles*perbus*20
            row['conditional_pv_pkm']=vehicles*perbus*a
        out['synthetic_reference_scenarios'][name]=row
    out['interpretation']='Emission proxies multiply synthetic AC charging energy by SIN factors; NOT actual purchased grid electricity, not annual optimized R0-R3 operation, and not F3 LCA. No grid tariff applied to charging-only AC.'
    return out

def main():
    if not SRC.is_file():raise SystemExit('Execute integrar_contratos_anuais_f1_f3_rev01.py antes')
    data=json.loads(SRC.read_text(encoding='utf-8'))
    out=calc(data)
    out['source_sha256']=hashlib.sha256(SRC.read_bytes()).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Parcelas quantitativas condicionais calculadas:',len(out['synthetic_reference_scenarios']),'cenários')
    print('F1/F3 finais:',out['F1'],out['F3'])
    print('Relatório:',OUT)
if __name__=='__main__':main()
