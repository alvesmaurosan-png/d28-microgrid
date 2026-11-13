# REV05.1 — Parametrização física condicionada R0–R3

Escopo: primeiro dia-fonte E100, REV09/REV12, 96 intervalos. Sem anualização, NSGA-II, aprovação científica ou integração econômica/ambiental.

**15 IDs selecionados:** D02-002; D05-001; D07-003/004/005/006/007/008/009/010; D08-001; D09-002/003/005; D13-001.

- **Entradas reais dos construtores:** teto FV, PCC, passo temporal, SOC inicial, SOH, eficiência de carga/descarga, eficiência CHP e PCI GN/biogás.
- **Verificações de consistência, não injeção em equação:** C-rate máximo, SOC mínimo/máximo, eficiência round-trip e fração mínima CHP. O construtor atual contém limites fixos (0,55; 0,10; 0,90; 0,50). O adaptador rejeita divergência; não afirma que esses quatro parâmetros sejam dinamicamente injetados.
- **Sem correspondência de design:** potência FV, capacidade BESS, PCS e CHP permanecem dimensionamentos experimentais; na Base Mestre são variáveis de projeto, não valores numéricos homologados.
- **R2 pendente:** composição/rendimento de metano, TRH, fração útil, densidade, auxiliares proporcionais ao CHP e dimensionamento físico do gasômetro/biodigestor. Produção exógena, gasômetro e estoque inicial permanecem valores experimentais explícitos.
- **CHP disponibilidade:** D09-004 é fração anual (0,96), não série binária; não é convertido em 96 valores de disponibilidade.
- **R3:** CGOB é atributo, não combustível nem crédito ambiental automático.
- **F1/F3:** permanecem diagnósticos sintéticos, sem qualquer revisão de sua definição científica.

## Execução

No PowerShell, na raiz do repositório com venv ativo:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python .\scripts\validar_parametrizacao_fisica_rev051.py
python -m pytest -q
```

O relatório `reports/D28_REV051_PARAMETRIZACAO_FISICA_CONDICIONADA.json` registra o SHA-256 das fontes, parâmetros, verificações e lacunas. **Este gate não fecha a parametrização física integral de R2**; explicita os bloqueios restantes, sem inventar entradas.
