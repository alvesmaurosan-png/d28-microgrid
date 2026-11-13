"""NSGA-II canônico genérico. Avaliador científico externo deve retornar F1,F2."""
import math
import random


def dominates(a, b):
    return all(x <= y for x,y in zip(a,b)) and any(x < y for x,y in zip(a,b))


def fronts(values):
    remaining = list(range(len(values)))
    result = []
    while remaining:
        front = [i for i in remaining if not any(dominates(values[j],values[i]) for j in remaining if j != i)]
        result.append(front)
        removed = set(front)
        remaining = [i for i in remaining if i not in removed]
    return result


def crowding(front, values):
    d = {i:0. for i in front}
    if len(front) <= 2:
        return {i:float('inf') for i in front}
    for k in range(2):
        order = sorted(front,key=lambda i:values[i][k])
        d[order[0]] = d[order[-1]] = float('inf')
        span = values[order[-1]][k]-values[order[0]][k]
        if span:
            for j in range(1,len(order)-1):
                d[order[j]] += (values[order[j+1]][k]-values[order[j-1]][k])/span
    return d


def run(evaluate, bounds, *, population=20, generations=10, seed=42):
    if population < 4 or population % 2 or generations < 1 or not bounds:
        raise ValueError("Configuração NSGA-II inválida")
    rng = random.Random(seed)
    names = list(bounds)
    if any(len(bounds[k]) != 2 or bounds[k][0] >= bounds[k][1] for k in names):
        raise ValueError("Domínio inválido")
    def sample():
        return {k:rng.uniform(*bounds[k]) for k in names}
    def score(x):
        v = evaluate(dict(x))
        if v is None or len(v) != 2 or any(not math.isfinite(float(z)) for z in v):
            return (float('inf'),float('inf'))
        return tuple(float(z) for z in v)
    pool = [sample() for _ in range(population)]
    scores = [score(x) for x in pool]
    for _ in range(generations):
        fs = fronts(scores)
        rank = {i:r for r,f in enumerate(fs) for i in f}
        dist = {i:d for f in fs for i,d in crowding(f,scores).items()}
        def tournament():
            i,j = rng.sample(range(len(pool)),2)
            return pool[min((i,j),key=lambda z:(rank[z],-dist[z]))]
        offspring = []
        while len(offspring) < population:
            a,b = tournament(),tournament()
            child = {}
            for k in names:
                lo,hi = bounds[k]
                alpha = rng.random()
                v = alpha*a[k]+(1-alpha)*b[k]
                if rng.random() < 1/len(names):
                    v += rng.gauss(0,(hi-lo)*0.1)
                child[k] = max(lo,min(hi,v))
            offspring.append(child)
        combined = pool+offspring
        values = scores+[score(x) for x in offspring]
        selected = []
        for f in fronts(values):
            ordered = sorted(f,key=lambda i:crowding(f,values)[i],reverse=True)
            selected += ordered[:population-len(selected)]
            if len(selected) == population:break
        pool = [combined[i] for i in selected]
        scores = [values[i] for i in selected]
    return {"population":pool,"objectives":scores,"nondominated_indices":fronts(scores)[0],
            "classification":"ALGORITHM_ONLY_UNTIL_VERIFIED_INTEGRATED_EVALUATOR"}
