"""Dominância exata em minimização; sem preenchimento de objetivos ausentes."""
import math

def nondominated(rows, keys=('F1','F2','F3')):
    valid=[]
    for row in rows:
        if row.get('feasible') is not True: continue
        try: vals=tuple(float(row[k]) for k in keys)
        except (ValueError,TypeError,KeyError): continue
        if not all(math.isfinite(v) for v in vals):continue
        valid.append((row,vals))
    result=[]
    for i,(row,vals) in enumerate(valid):
        dominated=any(j!=i and all(x<=y for x,y in zip(other,vals)) and any(x<y for x,y in zip(other,vals)) for j,(_,other) in enumerate(valid))
        if not dominated:result.append(row)
    return result

def triobjective_release_allowed(blockers):
    return all(blockers.get(b)=='FECHADO' for b in ('B01','B02','B03','B04','B05','B06','B07'))
