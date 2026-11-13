"""REV08.1d — auditoria F3 por arquitetura, sem alterar MILP nem EQ-045.
A ausência de atividade impede cálculo mesmo quando o fator está disponível.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from integrar_objetivos_rev081c import master_records, numeric

ROOT = Path(__file__).resolve().parents[1]
FACTOR_MAP = {
    'R0': ('D11-003','D11-013','D11-014','D11-017','D11-018','D11-019'),
    'R1': ('D11-003','D11-007','D11-013','D11-014','D11-015','D11-017','D11-018','D11-019'),
    'R2': ('D11-003','D11-005','D11-006','D11-007','D11-008','D11-009','D11-010','D11-013','D11-014','D11-016','D11-017','D11-018','D11-019'),
    'R3': ('D11-003','D11-007','D11-013','D11-014','D11-015','D11-017','D11-018','D11-019'),
}
BUCKETS = ('assets','replacements','operation','upstream','fugitive','eol')


def audit_architecture(architecture, records, *, annual_grid_kwh=None, design=None,
                       annual_fuel_nm3=None, annual_substrate_t=None,
                       annual_biogas_nm3=None, cgob_coverage_nm3=None,
                       annual_pkm=None, years=20):
    if architecture not in FACTOR_MAP:
        raise ValueError('Unknown architecture: '+str(architecture))
    if years != 20:
        raise ValueError('PC-REV08 requires explicit 20-year lifecycle')
    design = design or {}
    factors = {}
    blockers = []
    for factor in FACTOR_MAP[architecture]:
        rec = records.get(factor, {})
        value = rec.get('value')
        present = value is not None and value >= 0
        factors[factor] = {'name':rec.get('name'), 'unit':rec.get('unit'),
                           'value':value, 'status':'PRESENT_NOT_HOMOLOGATED' if present else 'MISSING'}
        if not present:
            blockers.append('MISSING_FACTOR:'+factor)
    evidence = {bucket:[] for bucket in BUCKETS}
    def component(bucket, name, amount, factor, units):
        if amount is None:
            blockers.append('MISSING_ACTIVITY:'+name)
            return
        if factor not in factors or factors[factor]['value'] is None:
            return
        if amount < 0:
            raise ValueError('Negative activity: '+name)
        evidence[bucket].append({'component':name,'kgco2e':amount*factors[factor]['value'],
                                 'activity':amount,'activity_unit':units,'factor_id':factor})
    component('assets','PV_initial',numeric(design.get('pv_kw')),'D11-003','kWp')
    component('assets','BESS_initial',numeric(design.get('bess_kwh')),'D11-013','kWh')
    if architecture != 'R0':
        component('assets','CHP_initial',numeric(design.get('chp_kw')),'D11-007','kWe')
    if architecture == 'R2':
        component('assets','biodigester',numeric(design.get('biodigester_t_per_year')),'D11-005','t/year')
        component('assets','gasometer',numeric(design.get('gasometer_m3')),'D11-006','m3')
    component('operation','grid_20y',annual_grid_kwh*years if annual_grid_kwh is not None else None,
              'D11-017','kWh')
    # Fuel, fugitives and substrate need verified activity and functional factors.
    if architecture in ('R1','R3'):
        if annual_fuel_nm3 is None:
            blockers.append('MISSING_ACTIVITY:annual_natural_gas_nm3')
        blockers.append('MISSING_LCA_BOUNDARY:natural_gas_combustion_and_upstream')
    if architecture == 'R2':
        if annual_biogas_nm3 is None:
            blockers.append('MISSING_ACTIVITY:annual_biogas_nm3')
        if annual_substrate_t is None:
            blockers.append('MISSING_ACTIVITY:annual_substrate_t')
        blockers.extend(['MISSING_LCA_BOUNDARY:biogenic_CO2_CH4_slip_and_leakage',
                         'MISSING_LCA_BOUNDARY:substrate_logistics_and_processing'])
    blockers.extend(['MISSING_LCA_BOUNDARY:PCS_CHARGERS_INVERTERS',
                     'MISSING_LCA_BOUNDARY:REPLACEMENTS',
                     'MISSING_LCA_BOUNDARY:END_OF_LIFE',
                     'MISSING_LCA_BOUNDARY:NONOVERLAPPING_INVENTORY'])
    if annual_pkm is None or annual_pkm <= 0:
        blockers.append('MISSING_OR_UNVERIFIED:annual_pkm')
    else:
        blockers.append('PKM_SYNTHETIC_NOT_HOMOLOGATED')
    cgob = {'physical_fuel':'NATURAL_GAS' if architecture=='R3' else None,
            'coverage_nm3_accounting':cgob_coverage_nm3 if architecture=='R3' else None,
            'physical_emission_deduction_kgco2e':0,
            'status':'ACCOUNTING_ONLY_NO_PHYSICAL_EMISSION_SUBSTITUTION' if architecture=='R3' else 'NOT_APPLICABLE'}
    if architecture=='R3' and cgob_coverage_nm3 is not None:
        if cgob_coverage_nm3 < 0: raise ValueError('Negative CGOB coverage')
        if annual_fuel_nm3 is not None and cgob_coverage_nm3 > annual_fuel_nm3:
            blockers.append('CGOB_COVERAGE_EXCEEDS_PHYSICAL_NATURAL_GAS_CONSUMPTION')
    return {'architecture':architecture,'status':'PARTIAL_LCA_ARCHITECTURE_SCOPED',
            'applicable_factor_ids':list(FACTOR_MAP[architecture]),'factors':factors,
            'partial_components':evidence,'blockers':sorted(set(blockers)),
            'F3_kgco2e_per_pkm':None,'scientific_pareto_eligible':False,
            'cgob':cgob,'lifecycle_years':years,
            'caution':'Partial components cannot be summed as complete LCA; no implicit zero for missing parts.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--annual',default='results/r0_annual_validation/annual_A_E100.json')
    args=parser.parse_args()
    master=ROOT/'data/raw/parametros/Base_Mestre_D28_PC_REV07_REV02.xlsx'
    records=master_records(master)
    annual=ROOT/args.annual
    if not annual.is_file():
        raise SystemExit('Missing annual R0 evidence: '+str(annual))
    source=json.loads(annual.read_text(encoding='utf-8'))
    if source.get('status')!='OPTIMAL' or source.get('experiment')!='R0_ANNUAL_A_E100':
        raise SystemExit('Annual evidence is not validated R0 A E100')
    design={'pv_kw':205.4806088017267,'bess_kwh':28272.75736597176,
            'pcs_kw':4996.651562474392}
    reports={a:audit_architecture(a,records,
                    annual_grid_kwh=source['grid_energy_kwh'] if a=='R0' else None,
                    design=design if a=='R0' else {},
                    annual_pkm=137675700.0 if a=='R0' else None)
             for a in FACTOR_MAP}
    result={'revision':'REV08.1d','status':'ARCHITECTURE_SCOPED_F3_AUDIT_ONLY',
            'sources_sha256':{'master':hashlib.sha256(master.read_bytes()).hexdigest(),
                              'r0_annual':hashlib.sha256(annual.read_bytes()).hexdigest()},
            'reports':reports}
    out=ROOT/'reports/D28_REV08_1D_F3_POR_ARQUITETURA.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for a,r in reports.items():
        missing=[k for k,v in r['factors'].items() if v['status']=='MISSING']
        print(a,'missing factors:',missing,'blockers:',len(r['blockers']))
    print('R3 CGOB: accounting only; physical fuel = natural gas')
    print('F3 final: unavailable for R0-R3; report:',out)

if __name__=='__main__':main()
