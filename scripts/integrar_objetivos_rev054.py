"""Integra F2 ao relatório REV05.3, sem alterar o despacho ou criar F1/F3."""
from pathlib import Path
import json

source=Path('reports/D28_REV052_FISICA_CONDICIONADA.json')
if not source.is_file():
    raise SystemExit('Relatório físico não encontrado: execute validar_fisica_r0_r3_rev052.py')
data=json.loads(source.read_text(encoding='utf-8'))
if not isinstance(data, dict) or not isinstance(data.get('results'), dict):
    raise SystemExit('Formato inesperado: relatório físico sem objeto results')
results=data['results']
result={}
for route in ('R0','R1','R2','R3'):
    if route not in results:
        raise SystemExit(f'Relatório físico sem arquitetura {route}')
    item=results[route]
    if item.get('optimal') is not True:
        raise SystemExit(f'{route}: despacho não ótimo')
    f2=float(item['peak_pcc_kw'])
    # O relatório armazena apenas o pico, não a série; integração de F2
    # a partir do indicador já extraído pelo solver, sem reconstruir a curva.
    result[route]={'F1':'BLOCKED_NO_APPROVED_ANNUAL_CONTRACT',
                   'F2_kw':f2,
                   'F3':'BLOCKED_NO_APPROVED_LIFECYCLE_INVENTORY',
                   'source':'D28_REV052_FISICA_CONDICIONADA.json'}
output=Path('reports/D28_REV054_OBJETIVOS_INTEGRADOS_CONDICIONADOS.json')
output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2,ensure_ascii=False))
print('Relatório:',output.resolve())
