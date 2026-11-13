# REV02 — Integração econômica da frota e infraestrutura

## Natureza do pacote
Overlay **aditivo**. Não substitui `r0_nsga2_milp.py`, não altera o MILP físico, não afirma que F1 integrada esteja conectada ao NSGA-II. Contém o contrato computacional, motor econômico independente e testes sintéticos. A matriz `REV03_Matriz_Economica_Integrada_Reconciliada.xlsx` é a referência documental, **não um arquivo homologado de parâmetros executáveis**.

## Instalação
Na raiz do repositório D28, copie `src/d28/economics/integrated_f1_rev02.py` e `tests/test_integrated_f1_rev02.py` preservando caminhos. Execute `python -m pytest -q tests/test_integrated_f1_rev02.py` e depois `python -m pytest -q`.

## Contrato de entrada
`evaluate_integrated_f1(scenario, annual, discount_rate, horizon_years, pcc_peak_kw, pcc_cap_kw)` recebe anos `t=0..H`, com CAPEX inicial em `t=0`, OPEX e PKM efetivamente atendidos em `t=1..H`, valores em R$ constantes 2026 e taxas reais. Todas as rubricas `COST_KEYS` são obrigatórias. Ausência é `None`; zero só com justificativa explícita em `provenance`. Residual é valor positivo subtraído da despesa no ano em que ocorre. Não lançar o mesmo custo em mais de uma rubrica.

## Fronteira de propriedade e dupla contagem
- `frota_*`: aquisição/reposição/manutenção dos veículos BEV, diesel e gás (desagregar em sistema de origem, somar uma vez no contrato).
- `infra_eletrica_*`: PV/BESS/PCS/carregadores/conexão, sem repetir custos já contidos no modelo energético.
- `infra_gas_*`: instalações de abastecimento, compressão, armazenamento e CHP quando aplicável.
- `reforco_rede_*`: somente BAU quando necessário, ou outros cenários se protocolo permitir explicitamente.
- `energia_eletrica`: compra faturada, contabilizando energia de recarga e auxiliares conforme balanço; `combustivel_diesel`, `arla`, `combustivel_gas` separados.
- `residual_*`: descontar apenas valores residuais comprovados, evitando duplicidade com valor de revenda no CAPEX.

## Integração posterior ao NSGA-II + MILP
1. NSGA-II propõe investimentos, infraestrutura e composição elegível da frota conforme cenário.
2. MILP resolve despacho e serviço; retorna `dispatch_feasible`, `pcc_peak_kw`, `pkm_atendidos` por ano e faturamento elétrico com fronteira definida.
3. Construtor de fluxos associa custos por tecnologia e ano com origem documental; distingue veículos existentes, novas compras, reposições e residuais.
4. `evaluate_integrated_f1` calcula F1 e F2 **somente após** validar serviço, todos os custos, evidências e despacho.
5. Se `PendingEvidence` ou MILP inviável: marcar candidato como **não avaliável** / inviável, registrar motivo; nunca apresentar penalidades `1e15/1e9` como valores científicos. A implementação de restrições no NSGA-II requer ajuste posterior controlado, não realizado neste overlay.

## Gates de homologação
- G-A: consistência da frota total 450 (hipótese sintética), plano, disponibilidade e despacho.
- G-B: igualdade da demanda de serviço/PKM de referência entre cenários; PKM atendidos validados.
- G-C: custos da frota BEV/diesel/gás documentados (ano, fonte, BRL 2026, unidade e validade).
- G-D: ativos elétricos/gás/rede reconciliados com Base Mestre, sem dupla contagem.
- G-E: calendário, vida útil, reposições, valor residual e taxa real reconciliados; conflito 8% vs 12% não resolvido por suposição.
- G-F: MILP anual, potência PCC, recarga individual e logística; bloqueios B01–B07 preservados.
- G-G: testes de conservação, sensibilidade, comparação de cenários e aprovação do pesquisador.

## Limites explícitos
- Cenários BAU/Realista/Cenario_1/Cenario_2; referências 2026/2030/2038 são pontos de trajetória, **não três compras independentes**.
- R0 histórico E100 permanece separado. A solução M8 não valida o custo da frota nem o PKM da REV02.
- Sem fontes novas comprovadas para CAPEX/OPEX BEV/diesel/gás, **não há valores F1 integrados reais**.
- A Base Mestre de 137 IDs não é alterada; o escopo de `D10-008` precisa de decisão documental e `D10-003` deve ser reconciliado antes de execução definitiva.
