"""M1: ingestão sem inferência de calendário ou homologação."""
from pathlib import Path
import csv, hashlib, json, collections, math

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def audit(root):
    root=Path(root)
    cross=read_csv(root/'docs/rastreabilidade/D28_Especificacao_Rastreabilidade_137_IDs.csv')
    ids=[r['ID'] for r in cross]
    blocks=read_csv(root/'docs/rastreabilidade/ESTADO_DOS_BLOQUEIOS.csv')
    solar=read_csv(root/'data/raw/solar/D28_solar_15min_REV12_1_3.csv')
    demand=read_csv(root/'data/raw/demanda/D28_REV09_demanda_15min.csv')
    counts=dict(collections.Counter(r['scenario'] for r in demand))
    errs=[]; warnings=[]
    if len(ids)!=137 or len(set(ids))!=137:errs.append('IDs: esperados 137 únicos')
    if len(solar)!=6720:errs.append(f'solar_15min: {len(solar)} != 6720')
    for s in ['E100','E200','E300','E375','E450']:
        if counts.get(s)!=6720: errs.append(f'{s}: {counts.get(s)} != 6720')
    def check_intervals(rows,label):
        starts=[int(r['interval_start_min']) for r in rows]; ends=[int(r['interval_end_min']) for r in rows]
        if starts != list(range(0,len(rows)*15,15)) or any(e-s!=15 for s,e in zip(starts,ends)):errs.append(label+': grade temporal inválida')
    check_intervals(solar,'solar')
    for s in counts:check_intervals([r for r in demand if r['scenario']==s],s)
    if len(set(r.get('solar_local_hour','') for r in solar))<len(solar):warnings.append('solar_local_hour repete por 15 min; não equivale a timestamp civil individual de cada intervalo (B01)')
    if any(r['estado'].upper() not in ['FECHADO','HOMOLOGADO'] for r in blocks):warnings.append('B01–B07 não encerrados: resultados científicos bloqueados')
    hashes={str(p.relative_to(root)):sha256(p) for p in sorted((root/'data/raw').rglob('*')) if p.is_file()}
    return {'status':'PASS_WITH_BLOCKERS' if not errs else 'FAIL','errors':errs,'warnings':warnings,'parameter_count':len(ids),'solar_rows':len(solar),'demand_by_scenario':counts,'blockers':blocks,'raw_sha256':hashes,'scientific_release_allowed':False}
