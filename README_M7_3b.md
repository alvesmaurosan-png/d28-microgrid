# M7.3b — Auditoria econômica de F1 (não invasiva)

Adiciona somente `src/d28/rev02/m7_3b_economic_audit.py` e `tests/test_rev021_m7_3b_economic_audit.py`. Não modifica código existente.

## Instalação
Extrair ZIP na raiz `D28_PC_REV08_REV02`.

## Execução
`python -m pytest -q`
`python -m d28.rev02.m7_3b_economic_audit --output results/m7_3b`

Sem `--input`, a auditoria retorna PENDING (nenhum custo inventado). Para auditar resultado real do avaliador, fornecer JSON contendo `costs` (campos de `IntegratedCosts`) e `f1_brl_per_pkm`: `python -m d28.rev02.m7_3b_economic_audit --input resultado.json --output results/m7_3b`.

A implementação existente `IntegratedCosts.f1_brl_per_pkm()` inclui `fleet_brl`; F1 definido pelo pesquisador exclui frota. Se `fleet_brl>0`, a auditoria reporta FAIL em `FLEET_SCOPE`, sem corrigir ou reescrever o avaliador. A reconciliação de fluxos anuais, desconto e dupla contagem permanece PENDING porque `IntegratedCosts` recebe apenas valores presentes agregados. A execução anual não é autorizada.
