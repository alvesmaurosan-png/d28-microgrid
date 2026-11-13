"""Orquestrador de elegibilidade PC-REV08/REV02.
Não altera o executor R0 nem executa otimização científica sem gates comprovados.
"""
from __future__ import annotations
import argparse, csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

YEARS = {2026: 100, 2030: 300, 2038: 450}
SCENARIOS = ('BAU', 'Realista', 'Cenario_1', 'Cenario_2')
ARCHITECTURES = ('R0', 'R1', 'R2', 'R3')
GATES = ('G-A', 'G-B', 'G-C', 'G-D', 'G-E', 'G-F', 'G-G')


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect(root, evidence):
    issues = []
    config_path = root / 'config' / 'rev02' / 'scenarios.json'
    if not config_path.is_file():
        raise FileNotFoundError(f'Contrato REV02 não encontrado: {config_path}')
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if config.get('protocol') != 'PC-REV08/REV02' or config.get('total_fleet') != 450:
        raise ValueError('Contrato REV02 incompatível com o protocolo de referência')
    if {int(k): v for k, v in config.get('years', {}).items()} != YEARS:
        raise ValueError('Trajetória de frota divergente da REV02')
    if set(config.get('scenarios', [])) != set(SCENARIOS):
        raise ValueError('Cenários divergentes da REV02')
    if config.get('status') != 'APPROVED':
        issues.append('PROTOCOL_REV02_NOT_FORMALLY_APPROVED')
    return config, issues, _sha(config_path)


def _gate_status(evidence, year, scenario, arch):
    """Aceita apenas evidência explícita por célula; nunca converte flags em aprovação automática."""
    key = f'{year}/{scenario}/{arch}'
    item = evidence.get('cells', {}).get(key, {})
    gates = item.get('gates', {})
    missing = [g for g in GATES if not isinstance(gates.get(g), dict)
               or gates[g].get('status') != 'PASS'
               or not gates[g].get('artifact_sha256')]
    # Evidência de todos os gates não substitui adaptador computacional validado.
    return missing


def build(root, evidence_path=None):
    evidence = {}
    if evidence_path:
        evidence = json.loads(Path(evidence_path).read_text(encoding='utf-8'))
        if evidence.get('protocol') != 'PC-REV08/REV02':
            raise ValueError('Manifesto de evidências com protocolo incorreto')
    config, issues, contract_hash = inspect(root, evidence)
    rows = []
    for year, bev in YEARS.items():
        for scenario in SCENARIOS:
            for arch in ARCHITECTURES:
                missing = _gate_status(evidence, year, scenario, arch)
                reasons = list(issues)
                if missing: reasons.append('EVIDENCE_GATES_MISSING:' + ','.join(missing))
                # O repositório disponibilizado só comprova executor integrado para R0 sintético.
                reasons.append('INTEGRATED_SCIENTIFIC_ADAPTER_NOT_VALIDATED')
                if arch != 'R0':
                    reasons.append('R1_R3_DISPATCH_F1_SERVICE_NOT_INTEGRATED')
                if scenario == 'BAU':
                    reasons.append('BAU_GRID_REINFORCEMENT_CAPEX_NOT_RECONCILED')
                else:
                    reasons.append('PCC_2500KW_AND_FULL_AC_BALANCE_NOT_CERTIFIED')
                if scenario in ('Realista', 'Cenario_2'):
                    reasons.append('INDIVIDUAL_SERVICE_AND_FLEET_MIX_NOT_CERTIFIED')
                rows.append({
                    'year': year, 'scenario': scenario, 'architecture': arch,
                    'fleet_total': 450, 'bev_reference': bev,
                    'pcc_limit_kw': '' if scenario == 'BAU' else 2500,
                    'status': 'BLOCKED_PENDING_EVIDENCE',
                    'F1_brl_per_pkm': '', 'F2_kw': '',
                    'reasons': ';'.join(dict.fromkeys(reasons)),
                    'contract_sha256': contract_hash,
                })
    return rows, {'protocol': 'PC-REV08/REV02',
                  'execution_class': 'EVIDENCE_GATED_MATRIX',
                  'scientific_homologation': False,
                  'matrix_cells': len(rows), 'executed': 0,
                  'blocked': len(rows), 'protocol_issues': issues,
                  'note': 'Matriz executável de gates; não substitui implementação anual R0-R3.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.', help='Raiz D28_MODELO_CONSOLIDADO')
    parser.add_argument('--output', default='results/rev02_matriz_controlada')
    parser.add_argument('--evidence', default=None, help='Manifesto opcional de evidências por célula')
    args = parser.parse_args(argv)
    rows, summary = build(Path(args.root), args.evidence)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'matriz_execucao.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    (out / 'resumo.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
