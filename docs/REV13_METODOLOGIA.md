# D28 REV13 — Intervalos críticos e auditoria da formulação binária

## Escopo
Análise **estática, reprodutível e sem otimização**. Usa os relatórios anuais REV12 `lp_physical`, `lp_protect-pcc`, `milp_physical` e a série anual de 35.040 intervalos. **Não modifica o MILP original e não calcula F1/F2**.

## Constatações da REV12
- LP physical: ótimo, 4 violações do PCC, máximo 1437,2332 kW, total 945,9939 kWh.
- LP protect-pcc: ótimo, sem violação do PCC, mas SOC abaixo/acima dos limites em 9/5 estados.
- MILP physical: limite de tempo, incumbente 186072,2132, limite inferior 945,9939, gap aproximadamente 99,49%. Não interpretar incumbente como mínimo estrutural.

## Auditoria binária
No `src/d28/dispatch/milp.py`, o modo binário `u_t` impõe `P_charge <= PCS*u_t` e `P_discharge <= PCS*(1-u_t)`. O relaxamento `u_t ∈ [0,1]` permite carga e descarga simultâneas, mas limita sua soma por `PCS`. A REV12 não gravou o despacho LP, portanto **não há evidência direta de simultaneidade** nem prova de que isso explique o gap. O script REV13 verifica a presença textual das equações e inspeciona as curvas nos instantes críticos, sem atribuir causalidade não demonstrada.

A REV12 também altera explicitamente o domínio das variáveis SOC e a restrição terminal para adicionar folgas. A penalização do SOC é somada sobre os estados, não uma energia adicional de bateria. Uma auditoria posterior deve confirmar se o `bess_energy_balance`, `pv_accounting`, `bess_initial` e o tratamento de energia terminal continuam ativos e coerentes.

## Uso
1. Extraia o ZIP na raiz do repositório (pasta `scripts/` e `docs/`).
2. Execute `python scripts\13_auditoria_intervalos_binarios.py --scenario E100 --window 8`.
3. Consulte `results/rev13_auditoria_E100.json` e `results/rev13_windows_E100.csv`.

O CSV apresenta oito intervalos antes e depois de cada ocorrência, a demanda, geração FV disponível e carga líquida. **Não apresenta SOC ou despacho otimizado**, pois não existem nas evidências REV12 fornecidas.

## Critérios de avanço
- Integridade da série confirmada por SHA-256.
- Identificação dos quatro intervalos LP por índice zero-based e dados temporais, se presentes no CSV.
- Auditoria textual da formulação, com ressalva de que não equivale a validação matemática.
- Antes de novo MILP anual: salvar séries completas de despacho LP (SOC, modo, carga, descarga, PV, rede), avaliar simultaneidade e testar janelas curtas, sem extrapolar factibilidade anual.
