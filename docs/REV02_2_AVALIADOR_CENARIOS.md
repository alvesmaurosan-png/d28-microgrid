# REV02.2 — Avaliador integrado de cenários

## Escopo
Overlay aditivo: **não modifica** o modelo MILP, a função de despacho, o algoritmo NSGA-II existente, a Base Mestre nem a matriz econômica. Integra os contratos já implementados em `integrated_f1_rev02.py` e `milp_f1_adapter_rev02.py`.

## Contrato
- `ScenarioCandidate`: ID, cenário, dimensionamento, `CertifiedDispatch`, lista completa `AnnualRecord` t=0..H, taxa de desconto, horizonte, limite PCC e identificação da origem econômica.
- `evaluate_candidate`: retorna `EVALUATED_CONDITIONAL` com F1/F2 ou `BLOCKED` com objetivos `None`. Não converte falhas em números de penalidade. Nenhum status implica homologação.
- `evaluate_scenario_comparison`: requer um candidato por cenário BAU, Realista, Cenario_1 e Cenario_2, sem duplicação; exige os mesmos PKM atendidos em cada ano, horizonte e taxa de desconto comuns. Resultado `COMPARABLE_CONDITIONAL` ou `BLOCKED`.

## Acoplamento futuro ao NSGA-II
1. Gerar a configuração do candidato e resolver o MILP **sem alterar** suas restrições.
2. Somente após término ótimo e carregamento das variáveis, extrair `import_pcc_kw` real de cada intervalo e criar `CertifiedDispatch` com identificador de execução verificável.
3. Produzir `AnnualRecord` de fonte econômica reconciliada independente. **Não** extrapolar automaticamente o ano elétrico para H anos nem presumir PKM pela carga elétrica.
4. Chamar `evaluate_candidate`. Encaminhar `(F1,F2)` ao NSGA-II somente se `status == 'EVALUATED_CONDITIONAL'`. Para `BLOCKED`, tratar restrição em camada explícita de factibilidade, nunca como objetivo científico.
5. Para comparar políticas, executar `evaluate_scenario_comparison` sobre candidatos previamente selecionados por regra documentada. A função não seleciona solução ótima nem produz Pareto.

## Limites e pendências
- Os testes são **sintéticos**. Os fluxos anuais reais, 137 IDs e status de evidências devem ser conectados por etapa posterior.
- O campo `provenance` no núcleo econômico atual exige texto não vazio; **não verifica independentemente homologação**. Não usar `COMPARABLE_CONDITIONAL` como homologação.
- A verificação de PKM é anual e numérica; não comprova por si só identidade de itinerários, passageiros ou nível de serviço.
- Os quatro cenários têm de usar convenção temporal, preço-base e horizonte coerentes; a função exige desconto/horizonte e PKM, mas a auditoria de preço-base ainda depende do contrato de dados.
- `f2_peak_pcc_kw` corresponde ao despacho fornecido; não comprova o máximo em outros anos se houver diferentes anos operacionais.

## Instalação e testes
Extrair ZIP na raiz `D28_PC_REV08_REV02` e executar:

```powershell
python -m pytest -q tests/test_scenario_evaluator_rev02_2.py
python -m pytest -q
```

Expectativa: 11 testes adicionais, total 381 se a base continuar com 370 e não houver mudanças paralelas. A suíte do repositório Windows deve ser executada pelo pesquisador.
