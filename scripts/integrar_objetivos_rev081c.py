"""REV08.1c: fechamento condicional de F1 e auditoria granular PKM/F3.
Não altera MILP nem transforma hipóteses em parâmetros homologados.
"""
from __future__ import annotations
import argparse, json, math, hashlib, sys
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from d28.objectives.pc_rev08_f1_f3 import f1_pc_rev08, REQUIRED_LCA

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def numeric(value):
    if value is None or isinstance(value,bool):return None
    try:
        v=float(str(value).strip().replace(',','.'))
        return v if math.isfinite(v) else None
    except (TypeError,ValueError):return None

def master_records(path):
    wb=load_workbook(path,read_only=True,data_only=True)
    try:
        sheet=wb['Parametros_137']
        it=iter(sheet.values)
        header=next(it)
        assert header[0]=='ID' and header[3]=='Valor REV20'
        return {str(r[0]):{'name':r[2],'raw':r[3],'value':numeric(r[3]),
                            'unit':r[4],'source':r[5]}
                for r in it if r[0] is not None}
    finally:wb.close()

def annual_pkm_basis(records, bev_count, *, total_fleet=None):
    ids=['D04-001','D04-002','D04-003','D04-004','D04-005','D04-006','D04-007']
    vals={k:records[k]['value'] for k in ids}
    if any(v is None or v<=0 for v in vals.values()):
        return {'annual_pkm':None,'blockers':['MISSING_D04_KM_CALENDAR_OCCUPANCY']}
    km=(vals['D04-001']*vals['D04-004']+
        vals['D04-002']*vals['D04-005']+
        vals['D04-003']*vals['D04-006'])
    per_bus=km*vals['D04-007']
    return {'annual_pkm':per_bus*bev_count,'annual_pkm_per_bus':per_bus,
            'annual_km_per_bus':km,'bev_count':bev_count,
            'total_fleet_assumption':total_fleet,
            'scope':'SYNTHETIC_BEV_ONLY_NOT_VERIFIED_SERVICE',
            'basis_ids':ids,
            'blockers':['PKM_OCCUPANCY_AND_OPERATIONAL_SCHEDULE_NOT_HOMOLOGATED']}

def cashflows(cfg, pv, bess, pcs, energy, *, annual_variable_bill=None):
    """20 anos explicitamente construídos; repetição anual = cenário condicional."""
    required=['pv_capex_brl_per_kwp','bess_capex_brl_per_kwh','pcs_capex_brl_per_kw',
              'engineering_contingency_fraction','pv_fixed_opex_fraction_of_pv_capex_year',
              'bess_fixed_opex_fraction_of_bess_capex_year','pcs_fixed_opex_fraction_of_pcs_capex_year',
              'discount_rate_real_year','horizon_years','pv_inverter_replacement_year',
              'pv_inverter_replacement_fraction_of_initial_pv_capex','bess_replacement_year',
              'bess_replacement_fraction_of_initial_bess_capex']
    if any(cfg.get(k) is None for k in required):raise ValueError('missing economics: '+str([k for k in required if cfg.get(k) is None]))
    if cfg['horizon_years']!=20:raise ValueError('PC-REV08 expects 20 years')
    p=pv*cfg['pv_capex_brl_per_kwp'];b=bess*cfg['bess_capex_brl_per_kwh'];c=pcs*cfg['pcs_capex_brl_per_kw']
    initial=(p+b+c)*(1+cfg['engineering_contingency_fraction'])
    fixed=(p*cfg['pv_fixed_opex_fraction_of_pv_capex_year']+
           b*cfg['bess_fixed_opex_fraction_of_bess_capex_year']+
           c*cfg['pcs_fixed_opex_fraction_of_pcs_capex_year'])
    variable=energy*cfg['energy_tariff_brl_per_kwh'] if annual_variable_bill is None else annual_variable_bill
    flows=[]
    for y in range(1,21):
        annual=fixed+variable
        if y==cfg['pv_inverter_replacement_year']:
            annual+=p*cfg['pv_inverter_replacement_fraction_of_initial_pv_capex']
        if y==cfg['bess_replacement_year']:
            annual+=b*cfg['bess_replacement_fraction_of_initial_bess_capex']
        flows.append(annual)
    return {'cf0_brl':initial,'annual_cashflows_brl':flows,'fixed_opex_brl_year':fixed,
            'variable_brl_year':variable,'initial_capex_brl':initial,
            'replacement_years':[cfg['pv_inverter_replacement_year'],cfg['bess_replacement_year']],
            'tariff_scope':'FLAT_ENERGY_ONLY' if annual_variable_bill is None else 'EXPLICIT_ANNUAL_BILL',
            'status':'EXPLORATORY_STATIONARY_20Y_NO_DEGRADATION'}

def lca_audit(records, energy_kwh, *, years=20, annual_pkm=None, design=None):
    rows={}
    for key in REQUIRED_LCA:
        r=records.get(key)
        rows[key]={'parameter':r['name'] if r else None,
                   'value':r['value'] if r else None,
                   'unit':r['unit'] if r else None,
                   'status':'NUMERIC_FACTOR_PRESENT_UNVERIFIED' if r and r['value'] is not None else 'MISSING_FACTOR'}
    # Granular coverage includes all six lifecycle buckets.
    inventory={k:{'kgco2e':None,'status':'INCOMPLETE','evidence':[],'missing':[]}
               for k in ('assets','replacements','operation','upstream','fugitive','eol')}
    pv=(design or {}).get('pv_kw')
    bess=(design or {}).get('bess_kwh')
    pv_factor=records.get('D11-003',{}).get('value')
    bess_factor=records.get('D11-013',{}).get('value')
    if pv is not None and pv_factor is not None:
        inventory['assets']['evidence'].append({'part':'PV_modules','kgco2e':pv*pv_factor,'id':'D11-003'})
    if bess is not None and bess_factor is not None:
        inventory['assets']['evidence'].append({'part':'BESS_initial','kgco2e':bess*bess_factor,'id':'D11-013'})
    inventory['assets']['missing']=['D11-014 PCS_and_chargers','D11-019 PV_inverters','ASSET_BOUNDARY_COMPLETENESS']
    inventory['replacements']['missing']=['REPLACEMENT_SCHEDULE_AND_EMBODIED_FACTORS']
    grid_factor=records.get('D11-017',{}).get('value')
    if grid_factor is not None and energy_kwh is not None:
        inventory['operation']['evidence'].append({'part':'grid_import_proxy',
            'kgco2e_20y':energy_kwh*grid_factor*years,'id':'D11-017',
            'status':'CONDITIONAL_REPEAT_20Y_SIN_HISTORIC_FACTOR'})
    inventory['operation']['missing']=['FULL_OPERATIONAL_LCA_BOUNDARY']
    inventory['upstream']['missing']=['D11-015 NATURAL_GAS','D11-016 SUBSTRATE_LOGISTICS','ARCHITECTURE_SPECIFIC_APPLICABILITY']
    inventory['fugitive']['missing']=['METHANE_MASS_BALANCE_AND_APPLICABILITY']
    inventory['eol']['missing']=['D11-018 END_OF_LIFE']
    return {'factors':rows,'buckets':inventory,
            'partial_components_not_additive_as_complete_LCA':True,
            'F3_kgco2e_per_pkm':None,
            'blockers':[k for k,v in rows.items() if v['status']=='MISSING_FACTOR']+
                       ['LCA_BUCKETS_NOT_COMPLETE','NONOVERLAP_BOUNDARIES_NOT_DOCUMENTED']}

def evaluate(data, records, cfg, *, bev_count=100, annual_bill=None):
    design=data['design']; energy=float(data['grid_energy_kwh']);peak=float(data['grid_peak_kw'])
    pkm=annual_pkm_basis(records,bev_count,total_fleet=450)
    economics=cashflows(cfg,design['pv_kw'],design['bess_kwh'],design['pcs_kw'],energy,
                        annual_variable_bill=annual_bill)
    pkm_annual=pkm['annual_pkm']
    conditional_f1=None
    if pkm_annual is not None:
        conditional_f1=f1_pc_rev08(economics['cf0_brl'],economics['annual_cashflows_brl'],
                                   [pkm_annual]*20,rate=cfg['discount_rate_real_year'])
    environmental=lca_audit(records,energy,annual_pkm=pkm_annual,design=design)
    return {'revision':'REV08_1C','candidate':'R0_A_E100',
            'status':'PARTIAL_OBJECTIVES_WITH_EXPLICIT_CONDITIONAL_F1',
            'F1_brl_per_pkm':None,'F1_conditional_brl_per_pkm':conditional_f1['F1_brl2026_per_pkm'] if conditional_f1 else None,
            'F2_physical_kw':peak,'F3_kgco2e_per_pkm':None,
            'F1_conditional_audit':conditional_f1,'cashflow':economics,
            'pkm_basis':pkm,'lca_audit':environmental,
            'scientific_pareto_eligible':False,
            'blockers':['F1_PKM_AND_ANNUAL_CASHFLOWS_CONDITIONAL',
                        'F1_TARIFF_AND_LIFECYCLE_COSTS_INCOMPLETE',
                        'F3_COMPLETE_LCA_MISSING',
                        'DISPATCH_POLICY_NOT_TRI_OBJECTIVE']}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--annual',default='results/r0_annual_validation/annual_A_E100.json')
    ap.add_argument('--bev-count',type=int,default=100)
    args=ap.parse_args()
    annual_path=ROOT/args.annual
    master=ROOT/'data/raw/parametros/Base_Mestre_D28_PC_REV07_REV02.xlsx'
    config=ROOT/'config/economics/r0_f1_exploratory_2026.json'
    if not annual_path.is_file():
        raise SystemExit('Missing annual solver output: '+str(annual_path))
    solver=json.loads(annual_path.read_text(encoding='utf-8'))
    if solver.get('status')!='OPTIMAL' or solver.get('experiment')!='R0_ANNUAL_A_E100':
        raise SystemExit('Annual result not validated R0 A E100')
    design={k:solver.get(k) for k in ('pv_kw','bess_kwh','pcs_kw')}
    if any(v is None for v in design.values()):
        # Exact validated design from REV05; require matching annual solver values if available.
        design={'pv_kw':205.4806088017267,'bess_kwh':28272.75736597176,'pcs_kw':4996.651562474392}
        design_status='REV05_RECORDED_FIXED_DESIGN_NOT_FROM_SOLVER_JSON'
    else:design_status='ANNUAL_SOLVER_JSON'
    inputs={'design':design,'grid_energy_kwh':solver['grid_energy_kwh'],'grid_peak_kw':solver['grid_peak_kw']}
    records=master_records(master);cfg=json.loads(config.read_text(encoding='utf-8'))
    report=evaluate(inputs,records,cfg,bev_count=args.bev_count)
    report['design_provenance']=design_status
    report['source_sha256']={'annual':sha(annual_path),'master':sha(master),'economics':sha(config)}
    out=ROOT/'reports/D28_REV08_1C_F1_PKM_F3_AUDITORIA.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('REV08.1c:',report['status'])
    print('F1 condicional:',report['F1_conditional_brl_per_pkm'])
    print('F2 físico:',report['F2_physical_kw'],'F3 completo:',report['F3_kgco2e_per_pkm'])
    print('PKM anual sintético:',report['pkm_basis']['annual_pkm'])
    print('Fatores ACV ausentes:',[k for k,v in report['lca_audit']['factors'].items() if v['status']=='MISSING_FACTOR'])
    print('Pareto elegível:',report['scientific_pareto_eligible'])
    print('Relatório:',out)

if __name__=='__main__':main()
