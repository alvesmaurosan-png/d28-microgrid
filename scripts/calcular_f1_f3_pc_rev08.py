"""Report source-based eligibility; no synthetic annual results."""
import json
from pathlib import Path
from d28.traceability.base_master import load_base_master
from d28.objectives.pc_rev08_f1_f3 import base_master_status

root=Path(__file__).resolve().parents[1]
base=root/'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'
records=load_base_master(base)
report={'equations':{'F1':'PC-REV08 EQ-040','F3':'PC-REV08 EQ-045'},
        'F1':{'value':None,'status':'REQUIRES_20_DOCUMENTED_ANNUAL_CF_AND_PKM'},
        'F3':{'value':None,'status':'REQUIRES_COMPLETE_NONOVERLAPPING_LCA_AND_20_ANNUAL_PKM',
              'factor_records':base_master_status(records)},
        'physical_dispatch':'UNCHANGED','annualization':'NOT_PERFORMED'}
out=root/'reports/D28_F1_F3_PC_REV08_EXECUTION_STATUS.json'
out.parent.mkdir(exist_ok=True,parents=True)
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,indent=2,ensure_ascii=False))
print('Relatório:',out)
