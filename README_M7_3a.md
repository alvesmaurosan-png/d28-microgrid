M7.3a — Auditoria físico-operacional exclusivamente sintética C1.
Não modifica qualquer código preexistente, nem NSGA-II nem MILP.
Instalação: Expand-Archive -Path "$env:USERPROFILE\Downloads\D28_M7_3a_AUDITORIA_FISICA.zip" -DestinationPath . -Force
Execução: python -m pytest -q
Execução: python -m d28.rev02.m7_3_physical_audit --output results/m7_3a
O relatório só valida uma instância sintética de 3 intervalos, não a garagem real nem o ano completo.
