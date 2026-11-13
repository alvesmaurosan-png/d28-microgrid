"""M7.2 — validação conservadora de contratos, sem otimização ou homologação."""
from __future__ import annotations
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .contracts import Scenario, contract, validate_fleet, validate_design

YEARS = (2026, 2030, 2038)
STATUSES = ('PASS', 'FAIL', 'PENDING', 'BLOCKED')


def check(code: str, status: str, detail: str) -> dict:
    if status not in STATUSES:
        raise ValueError('Status de auditoria inválido')
    return {'code': code, 'status': status, 'detail': detail}


def _fleet_check(spec, fleet):
    if fleet is None:
        return check('FLEET', 'PENDING', 'Composição de frota não fornecida')
    try:
        if not isinstance(fleet, dict) or set(fleet) != {'bev', 'diesel', 'gas'}:
            raise ValueError('Frota exige bev, diesel, gas')
        validate_fleet(fleet['bev'], fleet['diesel'], fleet['gas'], total=spec.total_fleet)
        bev = fleet['bev']
        if spec.scenario != Scenario.C2 and bev != spec.planned_bev:
            raise ValueError('BEV diverge do contrato de referência')
        if spec.enforce_all_bev_in_2038 and spec.year == 2038 and bev != spec.total_fleet:
            raise ValueError('2038 exige eletrificação integral neste cenário')
        return check('FLEET', 'PASS', 'Composição atende às regras contratuais verificáveis')
    except (ValueError, TypeError, KeyError) as exc:
        return check('FLEET', 'FAIL', str(exc))


def _design_check(spec, design, limits):
    if design is None:
        return check('DESIGN', 'PENDING', 'Dimensionamento não fornecido')
    if not isinstance(design, dict):
        return check('DESIGN', 'FAIL', 'Dimensionamento deve ser objeto JSON')
    if any(k not in design for k in ('pv_kw', 'bess_kwh', 'pcs_kw', 'chp_kw')):
        return check('DESIGN', 'FAIL', 'Quatro capacidades são obrigatórias')
    try:
        if not spec.local_pv_bess_chp and any(float(design[k]) != 0 for k in ('pv_kw','bess_kwh','pcs_kw','chp_kw')):
            raise ValueError('Tecnologias locais não elegíveis no cenário')
        if limits is None:
            return check('DESIGN', 'PENDING', 'Limites físicos homologados não fornecidos')
        validate_design(design, limits)
        return check('DESIGN', 'PASS', 'Capacidades dentro dos limites fornecidos; homologação externa não inferida')
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        return check('DESIGN', 'FAIL', str(exc))


def validate_one(scenario: Scenario | str, year: int, *, evidence: dict | None = None,
                 fleet: dict | None = None, design: dict | None = None,
                 limits: dict | None = None, request_annual: bool = False) -> dict:
    spec = contract(scenario, year)
    # Compatibilidade com entradas M7.2.1: evidence é ignorado, inclusive
    # quando contém declarações negativas. Não é condição de elegibilidade.
    checks = [
        check('CONTRACT', 'PASS', 'Contrato encontrado no módulo aprovado'),
        check('POLICY', 'PASS', 'Elegibilidade extraída do contrato, não inferida'),
        _fleet_check(spec, fleet),
        _design_check(spec, design, limits),
    ]
    checks.append(check('OPERATIONAL_MILP', 'PENDING' if spec.scenario == Scenario.C1 else 'BLOCKED',
        'M4–M6 demonstrativos disponíveis apenas para C1; execução operacional não realizada nesta auditoria'
        if spec.scenario == Scenario.C1 else 'Sem avaliador operacional individual M4–M6 habilitado para este cenário'))
    checks.append(check('F1_RECONCILIATION', 'PENDING',
        'Função econômica científica não reconciliada; proxy sintética não constitui homologação'))
    if request_annual:
        checks.append(check('ANNUAL_EXECUTION', 'BLOCKED', 'Execução anual bloqueada até validação físico-operacional e reconciliação econômica'))
    status = ('FAIL' if any(c['status']=='FAIL' for c in checks) else
              'BLOCKED' if any(c['status']=='BLOCKED' for c in checks) else
              'PENDING' if any(c['status']=='PENDING' for c in checks) else 'PASS')
    return {
        'scenario': spec.scenario.value, 'year': spec.year,
        'contract': {'planned_bev':spec.planned_bev, 'total_fleet':spec.total_fleet,
          'pcc_limit_kw':spec.pcc_limit_kw,
          'grid_upgrade_allowed':spec.grid_upgrade_allowed,
          'local_pv_bess_chp':spec.local_pv_bess_chp,
          'fleet_mix_optimizable':spec.fleet_mix_optimizable,
          'enforce_all_bev_in_2038':spec.enforce_all_bev_in_2038},
        'checks': checks, 'status':status, 'annual_authorized':False,
        'classification':'M7_2_CONTRACT_AUDIT_NOT_SCIENTIFIC_VALIDATION'
    }


def validate_matrix(inputs: dict | None = None, *, request_annual=False) -> dict:
    if inputs is None:
        inputs = {}
    if not isinstance(inputs, dict):
        raise ValueError('Entradas devem ser objeto JSON')
    # Chave: Scenario.value -> ano (string) -> {fleet, design, limits}; evidence legado ignorado.
    allowed = {'evidence','fleet','design','limits'}
    rows = []
    for scenario in Scenario:
        group = inputs.get(scenario.value, {})
        if not isinstance(group, dict):
            raise ValueError(f'Entrada inválida para {scenario.value}')
        for year in YEARS:
            item = group.get(str(year), {})
            if not isinstance(item, dict) or set(item) - allowed:
                raise ValueError(f'Entrada inválida para {scenario.value}/{year}')
            rows.append(validate_one(scenario, year, request_annual=request_annual, **item))
    return {'schema_version':'M7.2.2', 'generated_utc':datetime.now(timezone.utc).isoformat(),
            'records':rows, 'annual_authorized':False,
            'classification':'CONTRACT_ELIGIBILITY_AUDIT_ONLY_NO_DOCUMENTARY_GATE'}


def write_reports(result: dict, outdir: str | Path) -> tuple[Path, Path]:
    folder = Path(outdir)
    folder.mkdir(parents=True, exist_ok=True)
    jp, cp = folder/'m7_2_report.json', folder/'m7_2_checks.csv'
    jp.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    with cp.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['scenario','year','overall_status','code','status','detail'])
        writer.writeheader()
        for record in result['records']:
            for c in record['checks']:
                writer.writerow({'scenario':record['scenario'], 'year':record['year'],
                    'overall_status':record['status'], **c})
    return jp, cp


def main(argv=None):
    p = argparse.ArgumentParser(description='M7.2: auditoria de contratos, sem MILP ou NSGA-II')
    p.add_argument('--inputs', type=Path, help='JSON opcional de entradas por cenário/ano')
    p.add_argument('--output', type=Path, default=Path('results/m7_2'))
    p.add_argument('--request-annual', action='store_true')
    args = p.parse_args(argv)
    inputs = json.loads(args.inputs.read_text(encoding='utf-8-sig')) if args.inputs else None
    report = validate_matrix(inputs, request_annual=args.request_annual)
    jp, cp = write_reports(report, args.output)
    print('M7.2:', len(report['records']), 'cenários-ano auditados')
    for r in report['records']:
        print(r['scenario'], r['year'], r['status'])
    print('Relatórios:', jp, cp)
    print('Execução anual autorizada: NÃO')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
