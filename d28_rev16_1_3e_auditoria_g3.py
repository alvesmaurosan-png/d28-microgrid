#!/usr/bin/env python3
"""REV16.1.3e: consolidação G3 SOMENTE LEITURA, sem solver.
Executar na raiz do repositório. Escreve exclusivamente results/G3_REV16_1_3e/.
"""
import argparse, csv, hashlib, json, math, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'
DESIGNS=[{'pv_kw':1908.225,'bess_kwh':15000.0,'pcs_kw':5500.0},
         {'pv_kw':1908.225,'bess_kwh':20000.0,'pcs_kw':5500.0},
         {'pv_kw':1908.225,'bess_kwh':30000.0,'pcs_kw':5500.0}]
PKM=137675700.0
SOURCES={'series_sha256':ROOT/'data/processed/milp_inputs/R0_inputs_E100_15min.csv',
         'economics_sha256':ROOT/'config/economics/r0_f1_exploratory_2026.json',
         'runner_sha256':ROOT/'rodar_d28_rev16_1.py'}

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def read_json(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def num(obj,key):
    try:
        v=float(obj[key]);return v if math.isfinite(v) else None
    except (KeyError,TypeError,ValueError,OverflowError):return None

def close(a,b,atol=1e-6,rtol=1e-10):
    return a is not None and math.isclose(a,b,abs_tol=atol,rel_tol=rtol)

def check_report(report,design,source,require_runner):
    issues=[]
    if report.get('status')!='PASS':issues.append('status != PASS')
    if report.get('f3_excluded') is not True:issues.append('f3_excluded != true')
    for k,v in design.items():
        if not close(num(report.get('design') or {},k),v,atol=1e-7):issues.append('design.'+k+' incompatível')
    if not close(num(report,'annual_pkm'),PKM,atol=0.01):issues.append('annual_pkm incompatível')
    prov=report.get('provenance') or {}
    for k in ('series_sha256','economics_sha256'):
        if source.get(k) is None or prov.get(k)!=source[k]:issues.append('proveniência '+k+' incompatível')
    # Runner G3 usa original; candidato 3 foi obtido com runner temporário REV3d.
    if require_runner and prov.get('runner_sha256') and prov.get('runner_sha256')!=source.get('runner_sha256'):
        issues.append('runner_sha256 divergente')
    for k in ('f1_brl_per_pkm','f2_kw','solver_objective_brl','annual_energy_total_brl','present_energy_cost_brl'):
        if num(report,k) is None:issues.append('ausente/não finito: '+k)
    a=num(report,'solver_objective_brl');b=num(report,'annual_energy_total_brl')
    if a is not None and b is not None and abs(a-b)>0.01:issues.append('solver_objective != annual_energy_total (> R$0,01)')
    f1=num(report,'f1_brl_per_pkm');pv=num(report,'present_energy_cost_brl')
    # Não presumir que F1 = PV / PKM anual: VP(PKM) é diferente do PKM anual.
    return issues

def find_third():
    folders=sorted((RESULTS/'G3_correcao_numerica').glob('*/'),reverse=True)
    found=[]
    for folder in folders:
        p=folder/'DEPOIS_D28_REV16_1_R0_E100_ANUAL.json'
        summary=folder/'resumo.json'
        log=folder/'execucao.log'
        if not (p.exists() and summary.exists() and log.exists()):continue
        try:
            s=read_json(summary);r=read_json(p)
        except (ValueError,OSError):continue
        if s.get('runner_returncode')!=0 or s.get('runner_original_unchanged') is not True or s.get('cache_unchanged') is not True or s.get('outputs_restored') is not True:continue
        txt=log.read_text(encoding='utf-8',errors='replace')
        m=re.search(r'G3_RECONCILIACAO_NUMERICA=(\{[^\n]*\})',txt)
        if not m:continue
        try:d=json.loads(m.group(1))
        except ValueError:continue
        if d.get('n_corrected')!=10 or d.get('tolerance_kw')!=1e-6:continue
        found.append((folder,p,r,s,d))
    return found

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',default='results/G3_REV16_1_3e')
    args=ap.parse_args()
    source={k:sha(p) if p.exists() else None for k,p in SOURCES.items()}
    out=(ROOT/args.output).resolve()
    if out==RESULTS.resolve() or out==ROOT.resolve():ap.error('Diretório de saída deve ser dedicado')
    cachefile=RESULTS/'D28_G3_CACHE.json'
    if not cachefile.exists():raise SystemExit('BLOQUEADO: cache G3 ausente; nenhum MILP será executado')
    cache=read_json(cachefile)
    entries=cache.get('entries') or {}
    rows=[];evidence=[];flags=[]
    for i,design in enumerate(DESIGNS[:2],1):
        matched=[]
        for key,entry in entries.items():
            report=entry.get('report') or {}
            if all(close(num(report.get('design') or {},k),v,atol=1e-7) for k,v in design.items()):
                matched.append((key,entry,report))
        if len(matched)!=1:
            flags.append(f'Candidato {i}: {len(matched)} entradas de cache correspondentes (esperado 1)')
            rows.append({'candidate':i,'status':'UNVERIFIED'});continue
        key,entry,report=matched[0]
        issues=check_report(report,design,source,True)
        if issues:flags.extend(f'Candidato {i}: {x}' for x in issues)
        rows.append({'candidate':i,'status':'PASS' if not issues else 'UNVERIFIED','design':design,
                     'evidence_type':'CACHE_G3','cache_key':key,'cache_entry_source':entry.get('source'),
                     'f1_brl_per_pkm':num(report,'f1_brl_per_pkm'),'f2_kw':num(report,'f2_kw'),
                     'annual_energy_total_brl':num(report,'annual_energy_total_brl'),
                     'present_energy_cost_brl':num(report,'present_energy_cost_brl'),
                     'solver_objective_brl':num(report,'solver_objective_brl'),
                     'annual_pkm':num(report,'annual_pkm'),'issues':issues})
    third=find_third()
    if not third:
        flags.append('Candidato 3: nenhuma evidência REV16.1.3d completa encontrada')
        rows.append({'candidate':3,'status':'UNVERIFIED'})
    else:
        if len(third)>1:flags.append(f'Candidato 3: {len(third)} execuções REV3d válidas; selecionada a mais recente')
        folder,p,report,summary,diag=third[0]
        issues=check_report(report,DESIGNS[2],source,False)
        if issues:flags.extend('Candidato 3: '+x for x in issues)
        rows.append({'candidate':3,'status':'PASS' if not issues else 'UNVERIFIED','design':DESIGNS[2],
                     'evidence_type':'REV16.1.3d_ARCHIVE','evidence_path':str(p.relative_to(ROOT)),
                     'evidence_sha256':sha(p),'numerical_reconciliation':diag,
                     'f1_brl_per_pkm':num(report,'f1_brl_per_pkm'),'f2_kw':num(report,'f2_kw'),
                     'annual_energy_total_brl':num(report,'annual_energy_total_brl'),
                     'present_energy_cost_brl':num(report,'present_energy_cost_brl'),
                     'solver_objective_brl':num(report,'solver_objective_brl'),
                     'annual_pkm':num(report,'annual_pkm'),'issues':issues})
        evidence=[{'file':str(x.relative_to(ROOT)),'sha256':sha(x)} for x in (p,folder/'resumo.json',folder/'execucao.log')]
    # Auditoria econômica: divergência anual vs VP não é erro automaticamente.
    economic=[]
    for row in rows:
        if row['status']!='PASS':continue
        annual=row['annual_energy_total_brl'];pv=row['present_energy_cost_brl'];f1=row['f1_brl_per_pkm']
        economic.append({'candidate':row['candidate'],'annual_energy_total_brl':annual,
                         'present_energy_cost_brl':pv,'f1_brl_per_pkm':f1,
                         'implied_vp_pkm_if_numerator_equals_present_energy_cost':pv/f1 if f1 else None,
                         'vp_cost_to_annual_cost_ratio':pv/annual if annual else None})
    if len(economic)==3:
        by={x['candidate']:x for x in economic}
        a,b=by[2],by[3]
        economic.append({'comparison':'C3_MINUS_C2',
                         'delta_annual_brl':b['annual_energy_total_brl']-a['annual_energy_total_brl'],
                         'delta_present_brl':b['present_energy_cost_brl']-a['present_energy_cost_brl'],
                         'delta_f1_brl_per_pkm':b['f1_brl_per_pkm']-a['f1_brl_per_pkm']})
        den=[x['implied_vp_pkm_if_numerator_equals_present_energy_cost'] for x in (by[1],by[2],by[3])]
        if not math.isclose(min(den),max(den),rel_tol=1e-8):
            flags.append('VP(PKM) implícito difere entre candidatos; verificar numerador de F1 e convenção de desconto')
    # Pareto com tolerância F2 de 1e-6 kW, para evitar diferenças de arredondamento.
    passing=[r for r in rows if r['status']=='PASS']
    nondominated=[];dominance=[]
    for r in passing:
        dominated_by=[]
        for s in passing:
            if s is r:continue
            if (s['f1_brl_per_pkm']<=r['f1_brl_per_pkm']+1e-12 and
                s['f2_kw']<=r['f2_kw']+1e-6 and
                (s['f1_brl_per_pkm']<r['f1_brl_per_pkm']-1e-12 or s['f2_kw']<r['f2_kw']-1e-6)):
                dominated_by.append(s['candidate'])
        dominance.append({'candidate':r['candidate'],'dominated_by':dominated_by})
        if not dominated_by:nondominated.append(r['candidate'])
    if len(passing)!=3:flags.append('Consolidação incompleta: faltam relatórios integralmente verificados')
    # Condição metodológica: a diferença de PV requer decomposição explícita, não suposição de CAPEX.
    flags.append('AUDITORIA ECONÔMICA: composição de present_energy_cost_brl não demonstrada pelos indicadores agregados; decomposição CAPEX/OPEX/VP ainda requer evidência')
    report={'revision':'REV16.1.3e','created_utc':datetime.now(timezone.utc).isoformat(),
            'classification':'EXPLORATORY_NOT_HOMOLOGATED','no_milp_executed':True,
            'consolidation_status':'PASS_WITH_ECONOMIC_RESERVATION' if len(passing)==3 else 'INCOMPLETE',
            'source_sha256':source,'cache_sha256':sha(cachefile),'rows':rows,
            'economic_audit':economic,'dominance':dominance,'nondominated_sample':nondominated,
            'evidence':evidence,'findings':flags,
            'interpretation':'Amostra G3 R0/E100, F1 energético; não representa F1 integrado, NSGA-II ou cenários BAU/Realista/C1/C2.'}
    out.mkdir(parents=True,exist_ok=True)
    (out/'D28_REV16_1_3e_CONSOLIDACAO_G3.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    with (out/'D28_REV16_1_3e_CANDIDATOS.csv').open('w',newline='',encoding='utf-8-sig') as f:
        cols=['candidate','status','evidence_type','f1_brl_per_pkm','f2_kw','annual_energy_total_brl','present_energy_cost_brl','solver_objective_brl']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows({k:r.get(k) for k in cols} for r in rows)
    md=['# REV16.1.3e — Consolidação e auditoria econômica G3','',
        '**Classificação:** exploratória, não homologada. **MILPs executados nesta revisão:** zero.','',
        '| Candidato | Estado | F1 (R$/PKM) | F2 (kW) | Custo anual (R$) | VP informado (R$) |',
        '|---|---|---:|---:|---:|---:|']
    for r in rows:
        def fmt(k):return f"{r[k]:.9f}" if isinstance(r.get(k),(int,float)) else '—'
        md.append(f"| {r['candidate']} | {r['status']} | {fmt('f1_brl_per_pkm')} | {fmt('f2_kw')} | {fmt('annual_energy_total_brl')} | {fmt('present_energy_cost_brl')} |")
    md+=['','**Pontos não dominados da amostra:** '+str(nondominated),'',
         '## Ressalvas e pendências','']+['- '+x for x in flags]+['',
         'Não inferir CAPEX a partir da diferença entre custos anuais e VP. Conferir composição e VP(PKM) na implementação econômica.','',
         'O arquivo JSON registra hashes, proveniência e localização das evidências.']
    (out/'D28_REV16_1_3e_PARECER.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print('REV16.1.3e:',report['consolidation_status'])
    for r in rows:print('CANDIDATO',r['candidate'],r['status'],'F1=',r.get('f1_brl_per_pkm'),'F2=',r.get('f2_kw'))
    print('AMOSTRA NAO DOMINADA:',nondominated)
    print('PENDENCIAS:',len(flags))
    for flag in flags:print(' -',flag)
    print('ARQUIVOS:',out)
    return 0 if len(passing)==3 else 2

if __name__=='__main__':sys.exit(main())
