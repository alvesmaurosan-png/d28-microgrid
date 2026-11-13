# D28 — auditoria de liberação anual F1–F2

Copie `scripts/07_auditar_liberacao_anual.py` e `tests/test_rev07_gate_anual.py` para as pastas equivalentes do repositório atualizado. Execute:

```powershell
python -m pytest tests\test_rev07_gate_anual.py -q
python scripts\07_auditar_liberacao_anual.py
```

Saída: `results/rev07_gate_anual_f1_f2.json` com hashes SHA-256 de entradas, condições de bloqueio e lista de pendências.

**Não modifique `contrato_anual.json` para `APPROVED` apenas para passar o teste.** O mapeamento anual requer evidência, aprovação e séries de 96 intervalos por dia. O manifesto `config/annual_f1_f2_evidence.json` não é criado automaticamente: as declarações de aprovação exigem documentação e verificação humana independente. O script não substitui verificação de tarifas, F1, custos R2/R3, PKM ou validação anual do MILP/NSGA-II. Um status positivo significa apenas pré-condições documentais satisfeitas; não homologa resultados.

A contabilidade legada `annual_f1_f2` soma o custo de rede calculado pela tarifa do módulo econômico e `annual_fuel_cost_brl`, além de `incremental_present_value_brl`. A equivalência com os custos operacionais do despacho (`grid`, `fuel`, `production`, `gas_loss`, `auxiliary`) deve ser comprovada antes da execução científica. Valores zero para custos auxiliares e identidade R1/R3 não constituem evidência de homologação.
