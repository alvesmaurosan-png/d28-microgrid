import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/recuperar_evidencias_f3_rev081f1.py'
spec=importlib.util.spec_from_file_location('rev081f1',p); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_embedded_factor():
 assert m.number('135 kgCO2e/kWh de capacidade instalada')==135.0
 assert m.number('Pendente de fator ACV rastreÃ¡vel') is None
 assert m.number('0,5 / 1,5 Ã— E200') is None
def test_recovered_master_factors():
 rows=m.master_rows(Path('data/raw/parametros/Base_Mestre_D28_PC_REV07_REV02.xlsx'))
 assert m.evidence('R0','D11-013','FATORES_DE_EMISSAO',rows,None)[0]['value']==135
 assert not m.evidence('R0','D11-014','FATORES_DE_EMISSAO',rows,None)
def test_no_cross_architecture_annual():
 assert not m.evidence('R1','grid_20y','DADOS_DE_ATIVIDADE',{}, {'grid_energy_kwh':123})
 assert m.evidence('R0','grid_20y','DADOS_DE_ATIVIDADE',{}, {'grid_energy_kwh':123})
def test_r3_no_physical_substitution():
 assert not m.evidence('R3','annual_natural_gas_nm3','DADOS_DE_ATIVIDADE',{},None)

