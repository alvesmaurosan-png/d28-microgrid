"""M7.3b: auditoria economica NAO invasiva de F1; sem solver e sem homologacao."""
import argparse
import json
import math
from pathlib import Path
from .economics import IntegratedCosts

FIELDS = tuple(IntegratedCosts.__dataclass_fields__)

def audit_f1(costs, *, reported_f1=None, atol=1e-9, rtol=1e-9):
    """Audita VP ja contabilizados (BRL) e PKM descontado; nao infere fluxos ausentes."""
    checks=[]
    def add(code, status, detail, **extra):
        checks.append(dict(code=code,status=status,detail=detail,**extra))
    missing=[k for k in FIELDS if k not in costs or costs[k] is None]
    if missing:
        add('INPUT_COMPLETENESS','PENDING','Parcelas ausentes: '+', '.join(missing))
        return dict(status='PENDING',checks=checks,annual_authorized=False,
                    classification='M7_3B_ECONOMIC_AUDIT_ONLY')
    try:
        v={k:float(costs[k]) for k in FIELDS}
        if not all(math.isfinite(x) and x>=0 for x in v.values()):
            raise ValueError('Parcelas devem ser finitas e nao negativas')
        if v['discounted_pkm']<=0: raise ValueError('VP(PKM) deve ser positivo')
        if atol<0 or rtol<0 or not all(math.isfinite(x) for x in (atol,rtol)):
            raise ValueError('Tolerancias invalidas')
    except (ValueError,TypeError) as exc:
        add('INPUT_VALIDITY','FAIL',str(exc))
        return dict(status='FAIL',checks=checks,annual_authorized=False,
                    classification='M7_3B_ECONOMIC_AUDIT_ONLY')
    # Reconstrucao independente, sem chamar o metodo integrado para calcular o alvo.
    infra_net=(v['infrastructure_brl']+v['grid_reinforcement_brl']+
               v['energy_brl']+v['operations_brl']-v['residual_brl'])
    integrated_net=infra_net+v['fleet_brl']
    if infra_net<0:
        add('NET_COST','FAIL','Numerador energetico liquido negativo')
    else:
        add('NET_COST','PASS','Numerador energetico nao negativo')
    f1_scope=infra_net/v['discounted_pkm']
    f1_integrated=integrated_net/v['discounted_pkm']
    try:
        f1_method=IntegratedCosts(**v).f1_brl_per_pkm()
        ok=math.isclose(f1_method,f1_integrated,abs_tol=atol,rel_tol=rtol)
        add('INTEGRATED_RECONCILIATION','PASS' if ok else 'FAIL',
            'Metodo integrado versus soma independente',residual=abs(f1_method-f1_integrated))
    except ValueError as exc:
        add('INTEGRATED_RECONCILIATION','FAIL',str(exc))
    if v['fleet_brl']>max(atol,rtol*max(1,integrated_net)):
        add('FLEET_SCOPE','FAIL','Implementacao integrada inclui frota; escopo F1 definido exclui frota',
            fleet_brl=v['fleet_brl'])
    else:
        add('FLEET_SCOPE','PASS','Sem parcela material de frota no numerador')
    if reported_f1 is None:
        add('REPORTED_F1','PENDING','F1 publicado pelo avaliador nao fornecido')
    else:
        try:
            reported=float(reported_f1)
            if not math.isfinite(reported): raise ValueError('F1 nao finito')
            diff=abs(reported-f1_scope)
            ok=math.isclose(reported,f1_scope,abs_tol=atol,rel_tol=rtol)
            add('REPORTED_F1','PASS' if ok else 'FAIL',
                'F1 publicado versus F1 energetico reconciliado',residual=diff)
        except (ValueError,TypeError) as exc:
            add('REPORTED_F1','FAIL',str(exc))
    # Fluxos anuais e origem das parcelas nao estao no dataclass: nao presumir auditoria deles.
    add('TEMPORAL_DISCOUNT_AND_DUPLICATION','PENDING',
        'Somente VP agregados: fluxos anuais, descontos e dupla contagem nao verificaveis')
    status='FAIL' if any(x['status']=='FAIL' for x in checks) else ('PENDING' if any(x['status']=='PENDING' for x in checks) else 'PASS')
    return dict(status=status,checks=checks,f1_energy_infrastructure_brl_per_pkm=f1_scope,
                f1_integrated_with_fleet_brl_per_pkm=f1_integrated,
                fleet_effect_brl_per_pkm=v['fleet_brl']/v['discounted_pkm'],
                energy_infrastructure_numerator_brl=infra_net,
                annual_authorized=False,classification='M7_3B_ECONOMIC_AUDIT_ONLY')

def main(argv=None):
    p=argparse.ArgumentParser(description='M7.3b auditoria de F1 sem modificar modelo')
    p.add_argument('--input',help='JSON com costs e f1_brl_per_pkm do avaliador')
    p.add_argument('--output',default='results/m7_3b')
    args=p.parse_args(argv)
    if args.input:
        raw=json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
        result=audit_f1(raw.get('costs',{}),reported_f1=raw.get('f1_brl_per_pkm'))
    else:
        result=audit_f1({})
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    (out/'m7_3b_report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    import csv
    with (out/'m7_3b_checks.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['code','status','detail','residual','fleet_brl'],extrasaction='ignore')
        writer.writeheader();writer.writerows(result['checks'])
    print('M7.3b:',result['status'],'| execucao anual autorizada: NAO')
    for check in result['checks']: print(check['code'],check['status'],check['detail'])
    print('Relatorios:',out/'m7_3b_report.json',out/'m7_3b_checks.csv')
    return 0

if __name__=='__main__': raise SystemExit(main())
