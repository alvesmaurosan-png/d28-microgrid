#!/usr/bin/env python3
"""REV16.1.3d: pre-homologacao estatica; sem executar MILP/NSGA-II."""
import ast
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results' / 'D28_REV16_1_3d_PRE_HOMOLOGACAO.json'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(rel):
    p = ROOT / rel
    if not p.is_file():
        return None, {'path': rel, 'exists': False}
    meta = {'path': rel, 'exists': True, 'sha256': sha(p)}
    try:
        return json.loads(p.read_text(encoding='utf-8-sig')), meta
    except (ValueError, UnicodeError) as e:
        meta['error'] = str(e)
        return None, meta

def finding(code, state, detail, evidence=None):
    return {'id': code, 'status': state, 'detail': detail, 'evidence': evidence or []}

def main():
    refs = {
        'g1': 'results/D28_REV16_1_3c_G1_CONSOLIDADO.json',
        'pkm_evidence': 'config/annual_f1_f2_evidence.json',
        'economics': 'config/economics/r0_f1_exploratory_2026.json',
        'objectives': 'config/experiments/r0_objective_inputs.json',
    }
    data, files = {}, {}
    for k, rel in refs.items():
        data[k], files[k] = load(rel)
    findings = []
    g1 = data['g1']
    if not isinstance(g1, dict):
        findings.append(finding('G1_REFERENCE', 'BLOCKED', 'Relatorio consolidado ausente ou invalido', [refs['g1']]))
    else:
        rows = g1.get('rows', [])
        eps = [r.get('epsilon_kw') for r in rows if isinstance(r, dict)]
        ok = (g1.get('revision') == 'REV16.1.3c' and g1.get('gate') == 'G1'
              and g1.get('status') == 'PASS_R0_MILP_BILL_VP_RECONCILED'
              and eps == [2500, 2450, 2400, 2300]
              and all(r.get('status') == 'PASS' and r.get('gate') == 'PASS' for r in rows))
        findings.append(finding('G1_REFERENCE', 'CONSISTENT' if ok else 'REVIEW',
            'Estrutura e quatro resultados G1 verificados; isto nao homologa F1' if ok else 'Divergencia no relatorio G1', [refs['g1']]))
        if g1.get('classification') != 'EXPLORATORY_NOT_HOMOLOGATED':
            findings.append(finding('G1_CLASSIFICATION', 'REVIEW', 'Classificacao exploratoria nao preservada', [refs['g1']]))
    ev, ec, obj = (data[k] for k in ('pkm_evidence', 'economics', 'objectives'))
    if not all(isinstance(v, dict) for v in (ev, ec, obj)):
        findings.append(finding('PKM_FILES', 'BLOCKED', 'Um ou mais arquivos de evidencia PKM ausentes ou invalidos', [refs[k] for k in ('pkm_evidence','economics','objectives')]))
    else:
        approved = ev.get('annual_pkm_approved') is True and ec.get('annual_pkm_status') == 'APPROVED'
        findings.append(finding('PKM_APPROVAL_FLAGS', 'CONSISTENT' if approved else 'BLOCKED',
            'Indicadores de aprovacao documental presentes' if approved else 'PKM nao possui ambas as sinalizacoes de aprovacao exigidas no G2', [refs['pkm_evidence'],refs['economics']]))
        vals = [ec.get('annual_pkm'), obj.get('annual_pkm')]
        valid = all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0 for v in vals)
        equal = valid and math.isclose(vals[0], vals[1], rel_tol=1e-9, abs_tol=1e-6)
        findings.append(finding('PKM_VALUES', 'CONSISTENT' if equal else 'BLOCKED',
            'PKM numericamente coincidente entre configuracoes' if equal else 'PKM ausente, invalido ou divergente entre configuracoes', [refs['economics'],refs['objectives']]))
        findings.append(finding('PKM_SOURCE_TRACEABILITY', 'REQUIRES_HUMAN_REVIEW',
            'Flags e igualdade numerica nao comprovam origem, frota, viagens, ocupacao, metodologia, periodo e aprovacao por autoridade competente', [refs['pkm_evidence']]))
    # Apenas inspecao textual: nunca importa scripts do modelo.
    for rel in ('rodar_d28_rev16_1.py','auditar_d28_rev16_1_3c.py',
                'src/d28/optimization/economic_dispatch_f1f2.py'):
        p = ROOT / rel
        if not p.is_file():
            findings.append(finding('SOURCE_'+p.stem.upper(), 'REVIEW', 'Codigo-fonte nao localizado', [rel]))
            continue
        try:
            tree = ast.parse(p.read_text(encoding='utf-8-sig'))
            functions = [n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
            findings.append(finding('SOURCE_'+p.stem.upper(), 'INSPECTED',
                'Arquivo sintaticamente legivel; funcoes encontradas: '+', '.join(functions[:30]), [rel]))
            files['source_'+p.stem] = {'path':rel,'exists':True,'sha256':sha(p)}
        except (SyntaxError, UnicodeError) as e:
            findings.append(finding('SOURCE_'+p.stem.upper(), 'REVIEW', 'Falha de leitura/parse: '+str(e), [rel]))
    findings.extend([
        finding('NUMERATOR_SCOPE', 'REQUIRES_HUMAN_REVIEW', 'Conferir se VP(C_energia) inclui somente custos de energia ou tambem CAPEX, O&M e reposicoes; confrontar nomenclatura e equacoes com present_value e MILP'),
        finding('TIME_AND_DISCOUNT', 'REQUIRES_HUMAN_REVIEW', 'Conferir horizonte, taxa real/nominal, inflacao, reajustes, valor residual e coerencia de desconto de custo e PKM'),
        finding('TARIFF_SCOPE', 'REQUIRES_HUMAN_REVIEW', 'Conferir tarifa de energia, demanda mensal, tributos, posto tarifario, unidades e tratamento de pico'),
        finding('F1_G2', 'BLOCKED', 'Nenhuma homologacao de F1 ou autorizacao de execucao G2 e emitida por esta auditoria'),
    ])
    report = {'revision':'REV16.1.3d','scope':'STATIC_PRE_HOMOLOGATION_ONLY',
              'classification':'EXPLORATORY_NOT_HOMOLOGATED','decision':'G2_NOT_AUTHORIZED',
              'generated_at_utc':datetime.now(timezone.utc).isoformat(),
              'g1_closed_in_prior_stage':True,'files':files,'findings':findings,
              'restrictions':['NO_MILP','NO_NSGA2','NO_PARAMETER_CHANGES','NO_EPSILON_AS_DECISION_VARIABLE','NO_AUTOMATIC_APPROVAL']}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('REV16.1.3d | auditoria estatica concluida')
    for f in findings: print(f"{f['id']}: {f['status']} — {f['detail']}")
    print('DECISAO:',report['decision'])
    print('RELATORIO:',OUT)

if __name__ == '__main__': main()
