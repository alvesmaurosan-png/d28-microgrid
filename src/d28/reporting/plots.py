"""FIG-P01–P04. Gráficos exploratórios somente com dados válidos."""
from pathlib import Path

def plot_front(rows, out, title, keys=('F1','F2','F3')):
    if not rows: raise ValueError('Sem pontos elegíveis; nenhuma figura gerada')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    fig=plt.figure(figsize=(8,6))
    if len(keys)==3:
        ax=fig.add_subplot(111,projection='3d')
        ax.scatter([float(r[keys[0]]) for r in rows],[float(r[keys[1]]) for r in rows],[float(r[keys[2]]) for r in rows])
        ax.set_zlabel('F3 [kgCO₂e/PKM]')
    elif len(keys)==2:
        ax=fig.add_subplot(111)
        ax.scatter([float(r[keys[0]]) for r in rows],[float(r[keys[1]]) for r in rows])
    else:raise ValueError('Usar 2 ou 3 objetivos')
    labels={'F1':'F1 [BRL2026/PKM]','F2':'F2 [kW]','F3':'F3 [kgCO₂e/PKM]'}
    ax.set_xlabel(labels[keys[0]]);ax.set_ylabel(labels[keys[1]])
    ax.set_title(title);fig.tight_layout();fig.savefig(out,dpi=300);plt.close(fig)
    return out
