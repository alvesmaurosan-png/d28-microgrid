# PC-REV08/REV02 — Entrega inicial do núcleo computacional

## Estado real

**Executável para contratos, gates, testes, MILP elétrico simplificado e algoritmo NSGA-II genérico.**
**Não é ainda o modelo científico integrado definitivo.** Não são fornecidos resultados de otimização para os quatro cenários.

## Preservação

Todos os módulos existentes de `src/d28` permanecem inalterados. As novas interfaces estão em `src/d28/rev02`.
R0–R3 e G2/G3 permanecem históricos e não são renomeados como cenários.

## Implementado

- Contratos dos quatro cenários e anos 2026/2030/2038, frota física 450 e PCC 2500 kW onde aplicável.
- F1 integrado como composição explícita de valores presentes, com PKM descontado obrigatório.
- MILP energético PV+BESS com balanço AC, SOC e teto PCC; sem adicionar recarga à série agregada.
- Algoritmo NSGA-II genérico com nondominated sorting e crowding distance, sem avaliação científica fictícia.
- Gates de prontidão para impedir execução científica sem evidências.
- Testes unitários e de contrato.

## Não implementado / bloqueado

- BAU: custo de reforço de rede integrado à decisão de expansão (o núcleo exige capacidade explícita).
- Realista: comprovação de atendimento da logística e retenção diesel condicionada a déficit operacional demonstrado.
- Cenário 1: CHP com contrato de combustível e restrições físicas; presença mínima de cada tecnologia ainda sem decisão.
- Cenário 2: serviço por frota BEV/diesel/gás, combustível e abastecimento gasoso, ACV e custos integrados.
- Integração individual de recarga e despacho de viagens nos quatro cenários.
- Avaliador F1 integrado com todos os fluxos de CAPEX/OPEX/VP e PKM homologados.
- Acoplamento do NSGA-II a um avaliador científico MILP anual completo.
- Reconciliação do teto FV 1526,58 versus 1908,225 kWp, demais bloqueios B01–B07.

## Execução

No ambiente do usuário, após instalar dependências de `requirements.txt` e o pacote editável (`pip install -e .`):

```powershell
python run_rev02.py
python -m pytest tests/test_rev02_contracts.py tests/test_rev02_dispatch.py -q
```

O comando `run_rev02.py` informa **BLOCKED_PENDING_EVIDENCE** por desenho; não otimiza.

## Critério de aceite

A arquitetura e testes podem ser aceitos como **núcleo inicial**, não como integração final. Não transformar ausência de dados em defaults físicos ou econômicos.
