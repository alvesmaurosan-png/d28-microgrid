# REV02.1 — M5: CHP elétrico integrado (overlay experimental)

Adicionar os arquivos `src/d28/rev02/chp.py`, `src/d28/rev02/chp_integration.py` e `tests/test_rev021_m5_chp.py` à raiz do repositório. **Nenhum arquivo existente é substituído.**

A potência CHP entra no balanço elétrico M1–M3, o MILP decide ligar/desligar e potência, com disponibilidade, carga mínima, rendimento elétrico, consumo de combustível e orçamento opcional. A função objetivo operacional agrega tarifa de importação, combustível e O&M variável CHP. F2 mede a importação máxima; F1 sintético inclui CAPEX CHP e custos operacionais em VP, sem duplicar combustível em O&M. O calor recuperado é apenas informado: não há balanço térmico nem crédito econômico.

O avaliador M5 é **aditivo** e independente do avaliador M4: o NSGA-II ainda não otimiza `chp_kw` nesta entrega. Isto exige um próximo incremento de acoplamento, após os testes físicos. M5 é limitado ao Cenário 1 e usa parâmetros explícitos de demonstração, não homologados. Não inclui partida, rampas, tempo mínimo ligado/desligado, curva parcial de eficiência, suprimento real de biogás, emissões, inventário ACV ou séries anuais reais. **Não usar como resultado científico D28.**

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\D28_REV02_1_M5_CHP_OVERLAY.zip" -DestinationPath "." -Force
python -m pytest tests/test_rev021_m5_chp.py -q
python -m pytest -q
```

Base observada pelo usuário: 331 testes. Meta se cinco testes novos passarem: 336.
