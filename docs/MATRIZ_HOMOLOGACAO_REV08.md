# D28 — Matriz de homologação REV08

**Aprovações não presumidas.** O script REV08 indexa as evidências existentes, verifica consistência quantitativa básica das séries e registra impedimentos; não altera o contrato anual nem as equações do MILP.

| Decisão expressa necessária | Evidência já disponível | Condição objetiva para aprovação |
|---|---|---|
| H1. Calendário e séries anuais | `manifesto_anual.json`, `R0_inputs_manifest.json`, CSV E100–E450 | Aceitar explicitamente o contrafactual sintético, fornecer/validar o mapa completo de dias e justificar o alinhamento solar por posição de calendário |
| H2. Passageiros-km | `D28_REV08_1C_F1_PKM_F3_AUDITORIA.json` | Aprovar ocupação, km/ônibus e calendário operacional para cada cenário; o valor E100 é condicional |
| H3. Tarifas | `D28_AVALIACAO_TARIFARIA_REV07.json` | Definir tarifa de energia por período, demanda contratada, ultrapassagem, tributos e vigência; substituir proxy exploratório |
| H4. Parâmetros econômicos e F1 | Base Mestre e `D28_ECONOMIA_DESPACHO_ANUAL_REV04.json` | Conciliar investimentos, O&M, reposições, horizonte, taxa de desconto, custos anuais e valor presente; validar unidades e parcelas sem duplicação |
| H5. R2 — produção/perdas de biogás | `economic_dispatch_f1f2.py` | Homologar custos, volumes, perdas e fronteira contábil, sem duplicar combustível/produção |
| H6. R3 — CGOB | Modelo R3 e piloto econômico | Formalizar tratamento CGOB e demonstrar efeitos econômicos permitidos, sem créditos presumidos |
| H7. Auxiliares | Manifestos de recarga e entradas MILP | Definir fronteira da carga AC e impedir cobrança duplicada dos auxiliares |
| H8. Contrato anual e liberação | `contrato_anual.json`, relatório REV07, relatório REV08 | Somente após H1–H7: aprovar explicitamente contrato e evidências; reexecutar gate REV07 |

## Fechamento documental

`EVIDENCE_MANIFEST_PRESENT` e `EVIDENCE_REFERENCES` podem passar após executar `python scripts/08_reconciliar_evidencias.py`, **desde que todos os arquivos referenciados existam**. Isso não altera as aprovações técnicas, que permanecem bloqueadas até comprovação e decisão expressa.

## Limite da reconciliação

A verificação quantitativa automática cobre contagem de registros e concordância de energia anual entre manifestos; não constitui validação da formulação física, do despacho anual ou da contabilidade integral R0–R3.
