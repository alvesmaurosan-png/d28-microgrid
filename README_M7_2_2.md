# M7.2.2 — Retirada das exigências documentais

Substitui **somente** `src/d28/rev02/m7_validator.py` e
`tests/test_rev021_m7_2_validator.py`. Os demais módulos não são alterados.

- Retira todas as verificações `EVIDENCE.*` da matriz e da classificação.
- Aceita a chave legada `evidence` para compatibilidade, mas ignora seu conteúdo.
- Preserva `CONTRACT`, `POLICY`, `FLEET`, `DESIGN`, `OPERATIONAL_MILP`,
  `F1_RECONCILIATION` e bloqueio anual.
- `schema_version` atualizado para `M7.2.2`.
- Ajusta teste antigo de evidência falsa e adiciona um teste de compatibilidade.

Instalação na raiz do projeto:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\D28_REV02_1_M7_2_2_SEM_EXIGENCIAS_DOCUMENTAIS.zip" -DestinationPath . -Force
python -m pytest tests/test_rev021_m7_2_validator.py -v
python -m pytest -q
python -m d28.rev02.m7_validator --output results/m7_2_2
```

Meta: 351 testes, considerando os 350 previamente aprovados.
Não houve execução da regressão integral no ambiente Windows.
