# REV02.1 — Incremento operacional M1–M3 (experimental)

Este pacote é um **overlay**: copiar as pastas `src` e `tests` para a raiz do repositório D28_PC_REV08_REV02. Não substituir o repositório nem os arquivos existentes. O pacote inclui somente `src/d28/rev02/operational.py` e `tests/test_rev021_operational.py`.

- Mantém o núcleo NSGA-II + MILP existente inalterado.
- Introduz modelo independente Pyomo para energia de tração individual, janelas de disponibilidade, SOC por BEV, gabinete com potência compartilhada, número de conectores, PV, BESS e limite PCC.
- **Não inclui** CHP, frota a gás, expansão de rede, acoplamento ao NSGA-II, contratos D28 anuais ou função econômica F1 integrada. Não representa resultados científicos D28.
- Carga `base_load_kw` deve EXCLUIR a recarga dos BEVs modelados, evitando dupla contagem.
- `traction_kwh` é a energia de bateria consumida em cada intervalo (não potência). Disponibilidade `False` impede carregamento no intervalo.
- O limite 0,55 de C-rate é provisório, herdado do núcleo anterior; não homologado.

Execução no ambiente existente:

```powershell
python -m pytest tests/test_rev021_operational.py -q
python -m pytest -q
```

O histórico validado pelo usuário é 322 testes; os quatro novos testes devem elevar a contagem a 326 se a instalação estiver completa e não houver regressões.
