"""M7.3a: auditoria independente de solução C1 sintética, sem alterar o MILP."""
import argparse
import csv
import json
from pathlib import Path


def audit_model(model, *, abs_tol=1e-6, rel_tol=1e-7):
    import pyomo.environ as p
    if abs_tol <= 0 or rel_tol < 0:
        raise ValueError('Tolerancias invalidas')
    if not hasattr(model, '_rev021_chp'):
        raise ValueError('Auditoria M7.3a requer modelo C1 com CHP')
    groups = {
        'POWER_BALANCE': ['balance', 'pv_limit'],
        'BESS': ['bess_charge_limit','bess_discharge_limit','bess_transition','bess_initial','bess_terminal'],
        'BEV_CHARGING': ['bus_soc_bound','bus_initial','bus_terminal','bus_transition','availability',
                         'charge_limit','single_connection','connectors','cabinet_power'],
        'CHP_FUEL': ['chp_capacity','chp_availability','chp_minimum','chp_fuel_link','chp_fuel_budget'],
    }
    checks=[]
    def record(group, name, idx, residual, scale=1.0):
        limit=abs_tol+rel_tol*max(1.0,abs(scale))
        checks.append({'group':group,'constraint':name,'index':str(idx),
                       'residual':float(residual),'tolerance':float(limit),
                       'status':'PASS' if residual<=limit else 'FAIL'})
    for group,names in groups.items():
        for name in names:
            comp=getattr(model,name,None)
            if comp is None:
                if name=='chp_fuel_budget' and model._rev021_chp['parameters'].fuel_limit_kwh_lhv is None:
                    continue
                raise ValueError(f'Restricao obrigatoria ausente: {name}')
            for idx in comp:
                con=comp[idx]
                body=float(p.value(con.body,exception=True))
                if con.equality:
                    rhs=float(p.value(con.lower))
                    residual=abs(body-rhs)
                    scale=max(abs(body),abs(rhs))
                else:
                    lower=float(p.value(con.lower)) if con.has_lb() else None
                    upper=float(p.value(con.upper)) if con.has_ub() else None
                    residual=max(0., (lower-body) if lower is not None else 0.,
                                 (body-upper) if upper is not None else 0.)
                    scale=max([abs(body)]+([abs(lower)] if lower is not None else [])+
                              ([abs(upper)] if upper is not None else []))
                record(group,name,idx,residual,scale)
    # Bounds of all decision variables, including SOC and grid/PCC, plus integrality.
    for var in model.component_data_objects(p.Var, active=True):
        val=float(p.value(var,exception=True))
        if var.lb is not None:
            record('VARIABLE_BOUNDS',var.name,'lower',max(0.,float(var.lb)-val),max(abs(val),abs(float(var.lb))))
        if var.ub is not None:
            record('VARIABLE_BOUNDS',var.name,'upper',max(0.,val-float(var.ub)),max(abs(val),abs(float(var.ub))))
        if var.is_binary() or var.is_integer():
            record('INTEGRALITY',var.name,'integer',abs(val-round(val)),1.)
    for t in model.T:
        val=float(p.value(model.grid[t]))
        record('PCC_2500KW','grid',t,max(0.,val-2500.),2500.)
    for b in model.B:
        for t in model.T:
            # No charging during unavailable service; charging power is AC-side.
            unavailable=sum(float(p.value(model.charge[bb,c,t])) for bb,c in model.BC if bb==b)
            if all(float(p.value(model.connect[bb,c,t])) < 0.5 for bb,c in model.BC if bb==b):
                # Not a restriction on all buses when disconnected; charge must then be zero.
                record('BEV_CHARGING','charge_without_connection',(b,t),unavailable)
    summary={g:{'checks':sum(x['group']==g for x in checks),
                'max_residual':max(x['residual'] for x in checks if x['group']==g),
                'status':'PASS' if all(x['status']=='PASS' for x in checks if x['group']==g) else 'FAIL'}
             for g in dict.fromkeys(x['group'] for x in checks)}
    return {'revision':'M7.3a','classification':'SYNTHETIC_C1_PHYSICAL_AUDIT_NOT_D28_SCIENTIFIC_VALIDATION',
            'status':'PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL',
            'tolerances':{'absolute':abs_tol,'relative':rel_tol},'summary':summary,'checks':checks,
            'annual_authorized':False}


def run_synthetic(output='results/m7_3a'):
    from .operational import Bus,Cabinet,build_operational_milp
    from .chp import CHPParameters,attach_chp,solve_chp_operational
    # Two BEVs, three intervals, synthetic values; PCC cap exactly 2500 kW.
    buses=[Bus('A',50,100,10,100,(0,30,0),(True,False,True),50),
           Bus('B',40,100,10,100,(0,20,0),(True,False,True),40)]
    cabinets=[Cabinet('dual150',150,2,('A','B'))]
    model=build_operational_milp(buses=buses,cabinets=cabinets,
        base_load_kw=(80,80,80),pv_pu=(0,0,0),dt_hours=1,pcc_cap_kw=2500,
        tariff_brl_kwh=(1,1,1),bess_kwh=100,pcs_kw=50)
    params=CHPParameters(.4,.2,.01,(True,True,True),fuel_limit_kwh_lhv=500)
    attach_chp(model,capacity_kw=100,parameters=params,dt_hours=1)
    solved=solve_chp_operational(model)
    if solved['status']!='PASS_SYNTHETIC_OPERATIONAL_CHP':
        report={'revision':'M7.3a','status':'NOT_SOLVED','solver':solved,'annual_authorized':False}
        checks=[]
    else:
        report=audit_model(model)
        report['solver']={'status':solved['status'],'f2_kw':solved['f2_kw']}
        checks=report['checks']
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    (dest/'m7_3a_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with (dest/'m7_3a_checks.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['group','constraint','index','residual','tolerance','status'])
        writer.writeheader();writer.writerows(checks)
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='results/m7_3a')
    args=parser.parse_args();result=run_synthetic(args.output)
    print('M7.3a:',result['status'],'| execução anual autorizada: NÃO')
    for group,summary in result.get('summary',{}).items():
        print(group,summary['status'],'resíduo máximo',f"{summary['max_residual']:.3g}")
    print('Relatórios:',str(Path(args.output)/'m7_3a_report.json'),str(Path(args.output)/'m7_3a_checks.csv'))
    if result['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
