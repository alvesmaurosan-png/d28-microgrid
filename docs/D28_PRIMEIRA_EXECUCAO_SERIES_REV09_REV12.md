# Primeira execução com séries rastreáveis D28

Executar na raiz do repositório após instalar os patches anteriores:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python .\scripts\validar_d28_dia_fonte_r0_r3.py
python -m pytest -q
```

## Escopo e limites

- Dados de entrada efetivos: cenário E100, `day_index=0` (96 intervalos de 15 min) de `D28_REV09_demanda_15min.csv` e correspondência por `interval_start_min` em `D28_solar_15min_REV12_1_3.csv`.
- O relatório registra caminhos e SHA-256 dos dois arquivos e do contrato anual, sem atribuir a eles homologação.
- **Não é uma execução com parâmetros econômicos/ambientais homologados da Base Mestre**: capacidades, combustível, produção de biogás, tarifas, fatores de emissões e PKM são valores **diagnósticos** declarados no script, derivados do smoke anterior. F1 e F3 são apenas saídas do encadeamento, não indicadores científicos do D28.
- R2 usa produção de biogás exógena de diagnóstico; R3 não presume crédito ambiental de CGOB.
- `power_ac_kw` é demanda agregada AC. Não adicionar recarga individual ou auxiliares ao mesmo perfil.
- O modelo herda objetivo interno provisório de minimização da energia da rede; **não comprova despacho ótimo para F1/F3**.
- Contrato anual permanece pendente, sem extrapolação dos 96 intervalos a 8.760 horas. NSGA-II permanece bloqueado.
- Gate não deve ser promovido a resultado científico sem homologação de entradas, conciliação temporal e definição de objetivo interno.
