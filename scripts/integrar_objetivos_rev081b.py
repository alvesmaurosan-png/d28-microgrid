"""REV08.1b: liga contabilidade PC-REV08 ao candidato anual existente.
Sem completar lacunas de evidência por zeros ou repetição automática.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from d28.objectives.pc_rev08_f1_f3 import f1_pc_rev08,f3_pc_rev08

REQUIRED=('D11-014','D11-015','D11-016','D11-018','D11-019')
BUCKETS=('assets','replacements','operation','upstream','fugitive','eol')

def read(path):
    raw=Path(path).read_bytes()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def integrate(solver, rev04, rev06, rev07, contract=None):
    if solver.get('status')!='OPTIMAL' or solver.get('experiment')!='R0_ANNUAL_A_E100':
        raise ValueError('Despacho anual incompatível')
    if rev04.get('case')!='R0_A_E100' or rev06.get('case')!='R0_A_E100':
        raise ValueError('Contabilidade incompatível')
    if rev07.get('case') not in (None,'R0_A_E100'):
        raise ValueError('REV07 incompatível')
    energy=float(solver['grid_energy_kwh']);peak=float(solver['grid_peak_kw'])
    if not math.isclose(energy,float(rev06['annual']['grid_import_kwh']),abs_tol=.01):
        raise ValueError('Energia não conciliada')
    if not math.isclose(energy,float(rev04['dispatch']['grid_import_kwh_year']),abs_tol=.01):
        raise ValueError('REV04 não conciliada')
    if not math.isclose(peak,float(rev06['annual']['physical_peak_kw']),abs_tol=1e-5):
        raise ValueError('Pico não conciliado')
    econ=rev04['F1_components']; f3comp=rev04['F3_components']
    report={'revision':'REV08_1B','candidate':'R0_A_E100','status':'CONDITIONAL_OBJECTIVES_GATE',
            'physical':{'grid_kwh':energy,'F2_physical_kw':peak},
            'F1_brl_per_pkm':None,'F3_kgco2e_per_pkm':None,
            'F1_status':'BLOCKED','F3_status':'BLOCKED',
            'scientific_pareto_eligible':False,
            'conditional_components':{
                'initial_capex_brl':econ['conditional_initial_capex_brl'],
                'fixed_opex_brl_per_year':econ['conditional_fixed_opex_brl_year'],
                'flat_energy_brl_per_year':econ['energy_purchase_flat_tariff_exploratory_brl_year'],
                'grid_operational_tco2e_per_year':f3comp['conditional_grid_operational_emissions_tco2e_year']},
            'blockers':[], 'objective_equations':{'F1':'PC-REV08 EQ-040','F3':'PC-REV08 EQ-045'}}
    if contract is None:
        report['blockers'].append('MISSING_20_YEAR_CASHFLOW_PKM_AND_LCA_CONTRACT')
        return report
    # Explicit per-year data are mandatory: never infer 20 years from E100.
    try:
        f1=f1_pc_rev08(contract['cf0_brl'],contract['annual_cashflows_brl'],
                       contract['annual_pkm'],rate=contract['discount_rate_real'])
        report['F1_brl_per_pkm']=f1['F1_brl2026_per_pkm']
        report['F1_status']='CALCULATED_CONDITIONAL_NOT_HOMOLOGATED'
        report['F1_audit']=f1
    except (KeyError,ValueError,TypeError) as e:
        report['blockers'].append('F1: '+str(e))
    try:
        f3=f3_pc_rev08(ghg_components_kgco2e=contract['ghg_components_kgco2e'],
                       annual_pkm=contract['annual_pkm'],
                       factor_evidence=contract['factor_evidence'],
                       approved_credits_kgco2e=contract.get('approved_credits_kgco2e',0))
        report['F3_kgco2e_per_pkm']=f3['F3_kgco2e_per_pkm']
        report['F3_status']='CALCULATED_CONDITIONAL_NOT_HOMOLOGATED'
        report['F3_audit']=f3
    except (KeyError,ValueError,TypeError) as e:
        report['blockers'].append('F3: '+str(e))
    if report['F1_brl_per_pkm'] is not None and report['F3_kgco2e_per_pkm'] is not None:
        report['conditional_objective_vector']=[report['F1_brl_per_pkm'],peak,report['F3_kgco2e_per_pkm']]
        report['status']='TRIO_CALCULATED_CONDITIONAL_NOT_PARETO_ELIGIBLE'
        report['blockers'].append('DISPATCH_POLICY_MIN_GRID_ENERGY_NOT_TRI_OBJECTIVE')
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--contract',help='JSON com 20 fluxos, PKM anuais e inventário completo')
    a=p.parse_args()
    paths={
        'solver':ROOT/'results/r0_annual_validation/annual_A_E100.json',
        'rev04':ROOT/'reports/D28_ECONOMIA_DESPACHO_ANUAL_REV04.json',
        'rev06':ROOT/'reports/D28_FATURAMENTO_TEMPORAL_REV06.json',
        'rev07':ROOT/'reports/D28_AVALIACAO_TARIFARIA_REV07.json',
    }
    data={}; hashes={}
    for name,path in paths.items():
        if not path.exists():raise SystemExit('Arquivo ausente: '+str(path))
        data[name],hashes[name]=read(path)
    contract=None
    if a.contract:
        contract,hashes['contract']=read(Path(a.contract))
    result=integrate(**data,contract=contract)
    result['source_sha256']=hashes
    out=ROOT/'reports/D28_REV08_1B_OBJETIVOS_INTEGRADOS.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('REV08.1b:',result['status'])
    print('F1:',result['F1_brl_per_pkm'],'F2:',result['physical']['F2_physical_kw'],'F3:',result['F3_kgco2e_per_pkm'])
    print('Elegível Pareto:',result['scientific_pareto_eligible'])
    print('Bloqueios:',result['blockers'])
    print('Relatório:',out)
if __name__=='__main__':main()
