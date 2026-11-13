"""REV16.1: reconciliação anual F1/F2 com despacho de demanda mensal."""
from __future__ import annotations
import math
import calendar
from collections import defaultdict
from d28.economics.f1 import present_value
from d28.optimization.r0_r3_bridge import annual_contract_ready

def _valid(name, value):
    value=float(value)
    if not math.isfinite(value) or value<0: raise ValueError('INVALID_'+name)
    return value

def _close(name, a, b, tolerance):
    a=float(a); b=float(b)
    if abs(a-b)>max(tolerance,1e-8*max(abs(a),abs(b))):
        raise ValueError(name+'_MISMATCH')

def temporal_bill(grid_kw, grid_brl_kwh, months, dt_hours, demand_brl_kw_month):
    n=len(grid_kw)
    if not n or len(grid_brl_kwh)!=n or len(months)!=n: raise ValueError('SERIES_LENGTH_MISMATCH')
    dt=_valid('DT',dt_hours)
    if dt<=0:raise ValueError('INVALID_DT')
    demand=_valid('DEMAND_TARIFF',demand_brl_kw_month)
    peaks=defaultdict(float);energy=0.;cost=0.
    for g,rate,month in zip(grid_kw,grid_brl_kwh,months):
        g=_valid('GRID_KW',g);rate=_valid('GRID_PRICE',rate)
        if not isinstance(month,int) or month%100 not in range(1,13):raise ValueError('INVALID_MONTH')
        peaks[month]=max(peaks[month],g);energy+=g*dt;cost+=g*dt*rate
    demand_cost=sum(peaks.values())*demand
    return {'energy_kwh':energy,'energy_brl':cost,'demand_brl':demand_cost,
            'total_brl':cost+demand_cost,'monthly_peaks_kw':dict(sorted(peaks.items()))}

def annual_f1_f2_reconciled(route, *, cfg, design, grid_kw, months, dt_hours,
                             prices, annual_pkm, accounting, contract, dispatch_components,
                             evidence_approved=False, provenance=None, tolerance=1e-4,
                             dispatch_result=None):
    ready,reason=annual_contract_ready(contract)
    if not ready:raise ValueError('ANNUAL_CONTRACT_BLOCKED: '+reason)
    if not evidence_approved or not provenance:raise ValueError('HOMOLOGATED_EVIDENCE_REQUIRED')
    if route not in ('R0','R1','R2','R3'):raise ValueError('INVALID_ROUTE')
    year=int(contract['year']); n=(8784 if calendar.isleap(year) else 8760)*4
    if len(grid_kw)!=n or len(months)!=n or len(prices.grid_brl_kwh)!=n or dt_hours!=.25:
        raise ValueError('ANNUAL_15MIN_REQUIRED')
    expected=[year*100+month for month in range(1,13) for _ in range(calendar.monthrange(year,month)[1]*96)]
    if list(months)!=expected:raise ValueError('CALENDAR_MONTHS_MISMATCH')
    pkm=_valid('PKM',annual_pkm)
    if pkm<=0:raise ValueError('INVALID_PKM')
    if accounting is None:raise ValueError('ACCOUNTING_REQUIRED')
    if route!='R0' and not accounting.evidence:raise ValueError('ROUTE_EVIDENCE_REQUIRED')
    if route=='R3' and not accounting.cgob_accounting_rule:raise ValueError('CGOB_RULE_REQUIRED')
    if route=='R2' and prices.fuel_cost_includes_production and prices.production_brl_nm3>0:
        raise ValueError('R2_DOUBLE_COUNT')
    if route!='R2' and (prices.production_brl_nm3 or prices.gas_loss_brl_nm3 or prices.auxiliary_incremental_brl_kwh):
        raise ValueError('NON_R2_ROUTE_HAS_R2_COSTS')
    bill=temporal_bill(grid_kw,prices.grid_brl_kwh,months,dt_hours,cfg.demand_tariff_brl_per_kw_month)
    if max(grid_kw)>cfg.pcc_import_limit_kw+1e-6:raise ValueError('PCC_LIMIT_EXCEEDED')
    if not dispatch_components:raise ValueError('DISPATCH_COST_COMPONENTS_REQUIRED')
    c={k:_valid('DISPATCH_'+k,v) for k,v in dispatch_components.items()}
    expected_keys={'grid_brl','fuel_brl','production_brl','gas_loss_brl','auxiliary_incremental_brl'}
    if set(c)!=expected_keys:raise ValueError('DISPATCH_COMPONENTS_INCOMPLETE')
    _close('GRID_TARIFF_DISPATCH_ACCOUNTING',c['grid_brl'],bill['energy_brl'],tolerance)
    non_grid=sum(c[k] for k in expected_keys-{'grid_brl'})
    declared_fuel=accounting.annual_fuel_cost_brl
    if declared_fuel is not None:
        _close('ANNUAL_FUEL_COST_DISPATCH',declared_fuel,non_grid,tolerance)
    # Para tarifa positiva, a politica do MILP deve internalizar demanda mensal.
    # Reconstruimos a conta independentemente; nao somamos cost_brl novamente.
    if dispatch_result is None:
        if cfg.demand_tariff_brl_per_kw_month>0:
            raise ValueError('DEMAND_DISPATCH_EVIDENCE_REQUIRED')
    else:
        if dispatch_result.get('status')!='PASS' or not dispatch_result.get('checks') or not all(dispatch_result['checks'].values()):
            raise ValueError('MILP_NOT_CERTIFIED')
        policy=dispatch_result.get('objective')
        with_demand=dispatch_result.get('demand_charge_in_dispatch_objective') is True
        if cfg.demand_tariff_brl_per_kw_month>0 and (not with_demand or policy!='PILOT_ENERGY_PLUS_MONTHLY_DEMAND_BRL'):
            raise ValueError('DEMAND_DISPATCH_POLICY_REQUIRED')
        if with_demand and policy!='PILOT_ENERGY_PLUS_MONTHLY_DEMAND_BRL':
            raise ValueError('DISPATCH_POLICY_MISMATCH')
        if not with_demand and policy!='PILOT_VARIABLE_ENERGY_COST_BRL':
            raise ValueError('DISPATCH_POLICY_MISMATCH')
        if len(dispatch_result.get('grid_kw',[]))!=n:
            raise ValueError('DISPATCH_GRID_LENGTH_MISMATCH')
        for a,b in zip(grid_kw,dispatch_result['grid_kw']):
            _close('DISPATCH_GRID',a,b,tolerance)
        if set(dispatch_result.get('cost_components_brl',{}))!=expected_keys:
            raise ValueError('DISPATCH_COMPONENTS_INCOMPLETE')
        for k in expected_keys:
            _close('DISPATCH_COMPONENT_'+k,c[k],dispatch_result['cost_components_brl'][k],tolerance)
        _close('DISPATCH_DEMAND',_valid('DEMAND_COST',dispatch_result.get('demand_charge_brl')),bill['demand_brl'],tolerance)
        _close('DISPATCH_TOTAL',_valid('TOTAL_COST',dispatch_result.get('cost_brl')),
               bill['total_brl']+non_grid,tolerance)
        if with_demand and cfg.demand_tariff_brl_per_kw_month>0:
            peaks=dispatch_result.get('monthly_peak_kw',{})
            if set(peaks)!={str(m) for m in bill['monthly_peaks_kw']}:
                raise ValueError('MONTHLY_PEAK_KEYS_MISMATCH')
            for m,v in bill['monthly_peaks_kw'].items():
                _close('MONTHLY_PEAK_'+str(m),peaks[str(m)],v,tolerance)
    extra=accounting.incremental_present_value_brl
    if route!='R0' and extra is None:raise ValueError('ROUTE_CAPEX_PV_REQUIRED')
    extra=_valid('ROUTE_CAPEX_PV',extra or 0)
    annual_cost=bill['total_brl']+non_grid
    pv=present_value(cfg,design['pv_kw'],design['bess_kwh'],design['pcs_kw'],
                     annual_variable_bill_brl=annual_cost,annual_pkm=pkm)
    f1=(pv['pv_total_cost_brl']+extra)/pv['pv_pkm'];f2=max(grid_kw)
    if not all(math.isfinite(x) and x>=0 for x in (f1,f2)):raise ValueError('INVALID_OBJECTIVES')
    return {'objectives':(f1,f2),'units':('BRL/pkm','kW'),
            'audit':{'annual_grid_energy_brl':bill['energy_brl'],'annual_demand_brl':bill['demand_brl'],
                     'annual_non_grid_operating_brl':non_grid,'annual_total_operating_brl':annual_cost,
                     'present_cost_brl':pv['pv_total_cost_brl']+extra,'discounted_pkm':pv['pv_pkm'],
                     'dispatch_components_brl':c,'provenance':provenance,'f3_excluded':True,
                     'demand_reconciled':dispatch_result is not None}}
