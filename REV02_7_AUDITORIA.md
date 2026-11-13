# REV02.7 — Fechamento do contrato tarifário (escopo R0)

## Auditoria das fontes atuais enviadas

- `f1.py`: `annual_bill` cobra tarifa plana por kWh e soma picos mensais multiplicados pela tarifa de demanda. Não contém contrato, ultrapassagem, impostos ou diferenciação ponta/fora de ponta.
- `milp_adapter.py`: `attach_economic_objective` desativa o objetivo físico e minimiza o VP de custos fixos + fatura anual; `reconcile_economic_dispatch` compara esse objetivo com o valor presente da fatura reconstruída, **para a mesma solução carregada**.
- `milp.py`: `build_r0_milp` é modelo sintético PV–BESS R0, com importação não negativa, balanço e limites físicos. Nenhum modelo de frota R1–R3 foi fornecido.
- `r0_f1_exploratory_2026.json`: tarifa 0,75 R$/kWh, demanda 30 R$/kW/mês, 20 anos, desconto real 12%, PKM nulo, `EXPLORATORY_NOT_HOMOLOGATED`.

## Alterações aditivas nos dois módulos econômicos existentes

1. `TariffPolicy` em `f1.py`: tarifas por intervalo, contrato mensal explícito, tarifa de demanda, limiar e tarifa de ultrapassagem, adicional por kWh, cobrança fixa mensal e percentual aditivo sobre a fatura.
2. `annual_bill_regulated`: reconstrói faturamento ex post sem valores presumidos e exige 12 meses completos.
3. `attach_economic_objective(..., tariff_policy=...)`: acrescenta os mesmos termos como objetivo linear Pyomo, preservando comportamento legado quando a política é omitida.
4. `reconcile_economic_dispatch(..., tariff_policy=...)`: reconcilia com a mesma política e bloqueia divergências de política.

## Limites e gates

- **A política tarifária é uma parametrização explícita de cenário, não uma afirmação de aderência à regulação brasileira.** A regra de ultrapassagem `max(pico - multiplicador * contrato, 0)` e a cobrança de demanda `max(pico, contrato)` devem ser confrontadas com contrato, modalidade e normas aplicáveis.
- A cobrança tributária é representada por percentual **aditivo** sobre o subtotal, não cálculo tributário `por dentro`; requer comprovação antes de uso real.
- Não foi possível auditar a Base Mestre diretamente porque o ZIP enviado contém apenas cinco arquivos de código/configuração, sem o workbook.
- O arquivo JSON atual continua exploratório e **não** contém tarifa por intervalo, contrato ou alíquotas. Não foram inventados valores.
- A F1 calculada neste módulo continua restrita ao sistema energético PV–BESS R0; não representa F1 integrada frota + infraestrutura nem PKM homologados.
- Repetição de fatura anual por 20 anos e desconto real permanecem hipóteses estacionárias explícitas.
- Não foram modificados `milp.py`, `r0_nsga2_milp.py`, Base Mestre nem qualquer arquivo de cenário.

## Instalação

Faça backup dos dois módulos antes de extrair. O ZIP contém somente as versões revisadas de `src/d28/economics/f1.py`, `src/d28/economics/milp_adapter.py`, o teste `tests/test_tariff_reconciliation_rev02_7.py` e este documento.

Após extrair na raiz do projeto:

```powershell
python -m pytest -q tests/test_tariff_reconciliation_rev02_7.py -v
python -m pytest -q
```

Esperam-se 417 testes no total se os 411 existentes permanecerem e os 6 novos forem coletados. A validação Pyomo/HiGHS precisa ser feita no ambiente Windows do projeto.
