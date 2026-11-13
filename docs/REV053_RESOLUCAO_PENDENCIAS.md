# REV05.3 — Correção verificável das três pendências da REV05.2

## 1. Descarte versus perda física

`gas_curtailment[t]` é o **descarte operacional** que fecha a conservação de gás. O antigo nome `gas_loss` é mantido somente como alias de compatibilidade de relatórios. **Não é vazamento**. Perda física não é estimada, nem definida como zero. A formulação do PC-REV08, EQ-017, exige fundamentação para perdas; sem essa evidência, a validação científica do inventário de fugas continua bloqueada. Nenhuma emissão fugitiva pode ser calculada a partir do descarte.

## 2. Fronteira da demanda REV09

`gerar_calendario_anual.py` declara `base_load: not added; AC is charging-only` e calcula `power_ac_kw` a partir da potência de recarga. O verificador examina o código-fonte e a coerência AC potência/energia da série REV09, registrando SHA-256. **Não foi encontrado um manifesto que comprove por hash que esse CSV específico foi gerado por essa versão do script.** Logo, a semântica charging-only tem suporte documental, mas a linhagem arquivo-gerador permanece não demonstrada. O auxiliar de biodigestão não deve ser adicionado como carga de recarga individual nem subtraído novamente da geração CHP. Não promover esta evidência à condição de homologação.

## 3. Coerência obrigatória de R2

Quando `substrate_t_per_day` ou `digester_capacity_m3` são informados, `build_r2_milp` passa a exigir ambos e `physical_evidence` explícita, verificando em **todas** as chamadas: produção por intervalo = substrato × rendimento × Δt/24; volume ≥ substrato/densidade × TRH/fração útil; gasômetro ≥ vazão nominal CHP × autonomia. Divergências geram `ValueError` antes da construção do MILP. A configuração REV05.2 gerada por `conditional_r2_sizing` passa a fornecer a evidência rastreada pelos IDs D08-002, D08-003, D08-005, D08-006, D08-007 e D09-011.

Chamadas antigas sem substrato/volume permanecem como **protótipos exógenos condicionados**, não como validação do biodigestor.

## Decisão

As ambiguidades de código e a coerência dimensional podem ser encerradas **após regressão local**. A homologação científica integral continua impedida pela ausência de evidência da linhagem específica do CSV, parâmetros documentados de vazamento e suprimento efetivo de substrato. Não foram introduzidos fatores numéricos, tarifas, emissões ou hipóteses de disponibilidade. F1/F3, anualização e NSGA-II não são alterados.
