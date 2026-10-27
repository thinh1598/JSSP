"""Ve bieu do Gantt cua mot lich (de kiem tra bang mat). Hinh trong bao cao se ve bang cnsplots sau."""
from __future__ import annotations

from typing import Optional, Sequence

from .instance import JSSPInstance


def plot_gantt(inst: JSSPInstance, starts: Sequence[Sequence[int]], path: Optional[str] = None,
               title: Optional[str] = None) -> None:
    import matplotlib
    if path:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 0.55 * inst.n_machines + 2))
    cmap = plt.get_cmap("tab20")
    for l, job in enumerate(inst.jobs):
        for i, (m, d) in enumerate(job):
            ax.barh(m, d, left=starts[l][i], color=cmap(l % 20), edgecolor="black", linewidth=0.5)
            ax.text(starts[l][i] + d / 2, m, str(l), ha="center", va="center", fontsize=7)
    ax.set_yticks(range(inst.n_machines))
    ax.set_yticklabels([f"M{m}" for m in range(inst.n_machines)])
    ax.invert_yaxis()
    ax.set_xlabel("Thoi gian")
    ax.set_title(title or f"{inst.name}: Gantt (so trong o = chi so job)")
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=150)
        plt.close(fig)
    else:
        plt.show()
