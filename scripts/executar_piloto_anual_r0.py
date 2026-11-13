"""Piloto anual condicionado R0: reaproveita validador existente sem alterar MILP."""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'data/processed/milp_inputs/R0_inputs_E100_15min.csv'
MANIFEST = ROOT / 'data/processed/milp_inputs/R0_inputs_manifest.json'
VALIDATORS = {'A': ROOT/'scripts/validate_r0_annual_A.py',
              'B': ROOT/'scripts/validate_r0_annual_B.py',
              'C': ROOT/'scripts/validate_r0_annual_C.py'}

def inspect():
    if not INPUT.is_file() or not MANIFEST.is_file():
        raise FileNotFoundError('Entrada cronológica E100 ou manifesto não encontrado')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('solver_executions') != 0:
        # Valor histórico do manifesto não é prova de execução atual.
        pass
    if manifest.get('load_semantics') != 'charging_AC_only':
        raise ValueError('Semântica de carga inesperada; interrompido')
    with INPUT.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        required = {'load_charging_ac_kw', 'pv_kw_per_kwp', 'dt_hours'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Colunas cronológicas necessárias ausentes')
        count=0; load_kwh=0.; peak=0.
        for row in reader:
            load=float(row['load_charging_ac_kw']); pv=float(row['pv_kw_per_kwp']); dt=float(row['dt_hours'])
            if not (load >= 0 and pv >= 0 and abs(dt-.25)<1e-10):
                raise ValueError(f'Intervalo inválido: {count}')
            count+=1; load_kwh+=load*dt; peak=max(peak,load)
    if count != 35040:
        raise ValueError(f'Esperados 35040 intervalos; encontrados {count}')
    return {'scenario':'E100','intervals':count,'dt_hours':.25,
            'annual_charging_ac_kwh':round(load_kwh,6),
            'charging_peak_ac_kw':peak,
            'input_sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),
            'input_path':str(INPUT.relative_to(ROOT)),
            'source_manifest':str(MANIFEST.relative_to(ROOT)),
            'status':'PREFLIGHT_PASSED',
            'evidence':'SYNTHETIC_COUNTERFACTUAL_NOT_HOMOLOGATED',
            'caveats':['charging_only_no_nonvehicle_load', 'solar_calendar_alignment_not_same_observation_year',
                       'annual_solver_results_not_yet_certified']}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--execute',action='store_true',help='Executa MILP anual existente (pode demorar)')
    parser.add_argument('--design',choices=VALIDATORS,default='A')
    parser.add_argument('--time-limit',type=float,default=600.)
    args=parser.parse_args()
    if args.time_limit<=0: parser.error('--time-limit deve ser positivo')
    report=inspect();report['design']=args.design
    report['solver_executed']=False
    if args.execute:
        script=VALIDATORS[args.design]
        if not script.is_file(): raise FileNotFoundError(script)
        completed=subprocess.run([sys.executable,str(script),'--time-limit',str(args.time_limit)],cwd=ROOT,check=False)
        report['solver_executed']=True
        report['solver_process_returncode']=completed.returncode
        path=ROOT/f'results/r0_annual_validation/annual_{args.design}_E100.json'
        if path.is_file():
            run=json.loads(path.read_text(encoding='utf-8'))
            report['solver_status']=run.get('status')
            report['solver_result_path']=str(path.relative_to(ROOT))
            if run.get('status')=='OPTIMAL':
                report['annual_grid_energy_kwh']=run.get('grid_energy_kwh')
                report['annual_grid_peak_kw']=run.get('grid_peak_kw')
                report['status']='ANNUAL_R0_CONDITIONAL_OPTIMAL'
            else: report['status']='ANNUAL_R0_NOT_CERTIFIED'
        else: report['status']='ANNUAL_R0_NO_SOLVER_REPORT'
    target=ROOT/'reports/D28_PILOTO_OPERACIONAL_ANUAL_R0.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    print('Relatório:',target)
    if args.execute and report['status']!='ANNUAL_R0_CONDITIONAL_OPTIMAL': sys.exit(2)

if __name__=='__main__':main()
