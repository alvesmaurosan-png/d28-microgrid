# Mapa entre formulação e implementação (estado real da baseline)

| Escopo | Referência PC-REV08 | Código existente | Estado | Próxima evidência |
|---|---|---|---|---|
| Balanço AC/PCC/PV | Anexo A, A.4, EQ-001–... | `src/d28/dispatch/milp.py`: `build_r0_milp` | Protótipo sintético | T-004, T-005, T-006, verificação anual |
| BESS/SOC | A.5, EQ-... | `build_r0_milp` | Parcial; SOH exógeno | T-007 e política terminal aprovada |
| CHP GN | A.6 | Ausente no dispatcher R0 | Bloqueado B05 | T-008 |
| Biogás/biodigestor | A.6 | Ausente | Bloqueado B05 | T-009 |
| Recarga individual/gabinete duplo | A.7 | Ausente | Bloqueado B02 | T-010, T-011 |
| Demanda anual | A.8 | `data/processed/annual_charging/` | Sintética auditada; não homologada | B01, B02, T-012 |
| F1 econômico | A.9 | `src/d28/objectives/metrics.py` (inspecionar) | Não homologado | T-013, B03/B06 |
| F2 pico PCC | A.10 | Métricas e despacho | Condicionado ao MILP | T-014 |
| F3 ACV | A.11 | Não homologado | Bloqueado B04 | T-015 |
| NSGA-II/MILP | A.13 | `src/d28/optimization/nsga2.py` bloqueado | Não implementado | B07, T-P01–T-P10 |

**Obrigação de implementação:** antes de liberar cada componente, criar matriz por EQ (ID exato, símbolo, unidade, expressão, constraint, teste, status). Este mapa não atribui EQ exatos a módulos ainda não auditados; não renumerar equações. O arquivo `docs/rastreabilidade/D28_Especificacao_Rastreabilidade_137_IDs.csv` é a base de partida.
