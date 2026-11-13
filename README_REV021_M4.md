# REV02.1 M4 — Acoplamento operacional NSGA-II ↔ MILP

Overlay incremental. Copiar `src/` e `tests/` para a raiz de `D28_PC_REV08_REV02`.
Não substitui `integration.py`, `operational.py`, `nsga2.py` ou `dispatch.py`.

## Testes

```powershell
python -m pytest tests/test_rev021_m4_integration.py -q
python -m pytest -q
```

Referência informada pelo usuário: 326 testes aprovados. Meta: 331 testes.

## Limites

- Apenas demonstração sintética do Cenário 1, sem CHP, gás ou homologação D28.
- F1 é proxy econômica sintética; F2 é calculado do despacho individual.
- O avaliador propaga inviabilidade ao NSGA-II sem atribuir objetivos finitos.
- A escala anual sintética não equivale a séries de 8760 h homologadas.
- Não há garantia de que todos os candidatos sejam factíveis.
