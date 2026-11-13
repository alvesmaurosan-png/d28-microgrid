# REV02.1 — M7.2 Validador executável de contratos e elegibilidade

Pacote **aditivo**: `src/d28/rev02/m7_validator.py` e `tests/test_rev021_m7_2_validator.py`.
Não sobrescreve módulos existentes. Não executa MILP, NSGA-II ou modelo anual.

## Instalação e testes (PowerShell, raiz do projeto)

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\D28_REV02_1_M7_2_VALIDADOR_OVERLAY.zip" -DestinationPath "." -Force
python -m pytest tests/test_rev021_m7_2_validator.py -v
python -m pytest -q
```

Meta de regressão: **350 testes** (341 + 9), a confirmar no ambiente do usuário.

## Relatórios para os 12 pares cenário/ano

```powershell
python -m d28.rev02.m7_validator --output results/m7_2
```

Produz `results/m7_2/m7_2_report.json` e `results/m7_2/m7_2_checks.csv`.
Sem entradas adicionais, frota, dimensionamento, evidências e reconciliação
permanecem pendentes. Isto é intencional.

## Entradas opcionais

Um JSON com chave de cenário (`BAU`, `Realista`, `Cenario_1`, `Cenario_2`),
seguida de ano como texto (`2026`, `2030`, `2038`), com chaves opcionais
`fleet`, `design`, `limits`, `evidence`. Exemplo:

```json
{
  "Cenario_1": {
    "2026": {
      "fleet": {"bev": 100, "diesel": 350, "gas": 0},
      "design": {"pv_kw": 100, "bess_kwh": 200, "pcs_kw": 80, "chp_kw": 50},
      "limits": {"pv_kw": 1000, "bess_kwh": 1000, "pcs_kw": 550, "chp_kw": 300, "c_rate": 0.55}
    }
  }
}
```

Estes limites são **exemplo sintético**, não homologação. A flag
`evidence.<chave> = true` registra apenas uma declaração; não autentica
seu documento comprobatório. `false` é reprovação explícita; ausente é
pendência. `annual_authorized` é sempre `false`.

### Limites deliberados

- C2 possui `fleet_mix_optimizable=True`, mas o contrato atual **não**
  impõe eletrificação integral em 2038 para C2. O validador não inventa
  tal restrição.
- O contrato BAU não fixa PCC; o validador não cria teto fictício.
- A função econômica F1 científica continua pendente.
- A auditoria contratual não comprova factibilidade física.
