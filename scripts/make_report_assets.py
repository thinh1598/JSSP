"""Sinh hinh (PDF) va bang (LaTeX) cho bao cao tu results/raw/summary.csv.

    python scripts/make_report_assets.py

Dau ra: report/figures/*.pdf, report/tables/*.tex.
Hinh ve bang matplotlib; moi phan style nam trong apply_style() de sau nay doi sang cnsplots (yeu cau cua de bai)
chi can sua mot cho. Tat ca con so deu doc tu summary.csv, khong go tay.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib                      # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt        # noqa: E402

from jssp import analysis as an        # noqa: E402

SUMMARY = ROOT / "results" / "raw" / "summary.csv"
FIG = ROOT / "report" / "figures"
TAB = ROOT / "report" / "tables"

COLS = an.MAIN_COLS
NAME = {"inc_binary": "Inc. SAT", "binary": "SAT (bisect)", "cpsat": "CP-SAT", "gurobi": "Gurobi MIP",
        "cpo": "CP Optimizer", "cplex": "CPLEX MIP"}
# Okabe-Ito: phan biet duoc cho nguoi mu mau; ket hop kieu net/diem de khong chi dua vao mau
COLOR = {"inc_binary": "#0072B2", "binary": "#56B4E9", "cpsat": "#009E73", "gurobi": "#D55E00",
         "cpo": "#000000", "cplex": "#CC79A7"}
MARK = {"inc_binary": "o", "binary": "s", "cpsat": "^", "gurobi": "v", "cpo": "D", "cplex": "P"}


def apply_style() -> None:
    plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
                         "legend.frameon": False, "pdf.fonttype": 42, "figure.dpi": 150})


def inst_list(rows):
    return [n for n in an.instance_order(rows.values())
            if not any(r.trivial for r in rows.values() if r.instance == n)]


# ---------------------------------------------------------------- hinh 1: cactus
def fig_cactus(rows) -> None:
    fig, ax = plt.subplots(figsize=(5.2, 3.3))
    for m, s in COLS:
        ts = sorted(r.time for r in rows.values()
                    if r.method == m and r.solver == s and r.optimal and not r.trivial)
        ax.step(range(1, len(ts) + 1), ts, where="post", color=COLOR[m], lw=1.4, label=NAME[m])
        ax.plot(range(1, len(ts) + 1), ts, MARK[m], color=COLOR[m], ms=4)
    ax.set_yscale("log")
    ax.set_xlabel("Number of instances proven optimal")
    ax.set_ylabel("Time (s, log scale)")
    ax.legend(ncol=2, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "cactus.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- hinh 2: khoang [LB,UB] bac lon
def fig_large_bounds(rows) -> None:
    names = [n for n in an.TIER_ORDER["large"] if any((n, m, s) in rows for m, s in COLS)]
    fig, axes = plt.subplots(1, len(names), figsize=(7.2, 2.7), sharey=True)
    if len(names) == 1:
        axes = [axes]
    order = [c for c in reversed(COLS) if any((n, c[0], c[1]) in rows for n in names)]
    for ax, n in zip(axes, names):
        for k, (m, s) in enumerate(order):
            r = rows.get((n, m, s))
            if r is None:
                continue
            ax.plot([r.lb, r.ub], [k, k], color=COLOR[m], lw=3.2, solid_capstyle="butt")
            ax.plot([r.lb], [k], "|", color=COLOR[m], ms=9)
            if r.optimal:
                ax.plot([r.ub], [k], "*", color=COLOR[m], ms=9)
        ax.set_title(n, fontsize=9)
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels([NAME[m] for m, _ in order])
        ax.tick_params(axis="x", labelsize=7)
        ax.grid(axis="y", alpha=0)
    fig.supxlabel("Makespan (bar = proven [lower, upper] bound; star = proven optimal)", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "large_bounds.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- hinh 3: thoi gian bac nho + vua
def fig_times(rows) -> None:
    names = [n for n in inst_list(rows) if an.tier_of(n) in ("small", "medium")]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    width = 0.8 / len(COLS)
    for k, (m, s) in enumerate(COLS):
        xs, ys, xt, yt = [], [], [], []
        for i, n in enumerate(names):
            r = rows.get((n, m, s))
            if r is None:
                continue
            x = i + (k - (len(COLS) - 1) / 2) * width
            if r.optimal:
                xs.append(x)
                ys.append(max(r.time, 0.1))
            else:
                xt.append(x)
                yt.append(an.budget_of(n))
        ax.plot(xs, ys, MARK[m], color=COLOR[m], ms=4, label=NAME[m])
        ax.plot(xt, yt, "x", color=COLOR[m], ms=5)
    ax.set_yscale("log")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Time (s, log scale)")
    ax.text(0.99, 0.02, "x = time limit reached", transform=ax.transAxes, ha="right", fontsize=7)
    ax.legend(ncol=3, fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "times_small_medium.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- bang
def esc(s: str) -> str:
    return s.replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def cell(r) -> str:
    if r is None:
        return "--"
    if r.optimal:
        return f"{r.time:.1f}"
    return f"[{r.lb},\\,{r.ub}]"


def tab_main(rows) -> None:
    names = inst_list(rows)
    lines = [r"\begin{tabular}{llr" + "r" * len(COLS) + "}", r"\toprule",
             "Instance & Size & Opt. & " + " & ".join(NAME[m] for m, _ in COLS) + r" \\", r"\midrule"]
    last_tier = None
    for n in names:
        t = an.tier_of(n)
        if last_tier is not None and t != last_tier:
            lines.append(r"\midrule")
        last_tier = t
        cells = {(m, s): rows[(n, m, s)] for m, s in COLS if (n, m, s) in rows}
        smp = next(iter(cells.values()))
        w = an.winner(cells)
        opt = [r.ub for r in cells.values() if r.optimal]
        out = []
        for j, (m, s) in enumerate(COLS):
            c = cell(cells.get((m, s)))
            out.append(r"\textbf{" + c + "}" if w == (m, s) else c)
        lines.append(f"{esc(n)} & {smp.n_jobs}$\\times${smp.n_machines} & {opt[0] if opt else '--'} & "
                     + " & ".join(out) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "main.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tab_summary(rows) -> None:
    data = an.summary_by_method(rows, COLS)
    lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
             r"Tier (limit) & Method & Solved & PAR2 (s) & Gap (\%) & RAM (MB) \\", r"\midrule"]
    last = None
    for d in data:
        if last is not None and d["tier"] != last:
            lines.append(r"\midrule")
        tier = f"{d['tier'].capitalize()} ({d['budget_s']} s)" if d["tier"] != last else ""
        last = d["tier"]
        gap = f"{d['mean_gap_unsolved_pct'] + 1e-9:.1f}" if d["mean_gap_unsolved_pct"] != "" else "--"
        mem = f"{d['mean_peak_mem_mb']:.0f}" if d["mean_peak_mem_mb"] != "" else "--"
        meth = {an.LABEL[m]: NAME[m] for m, _ in COLS}[d["method"]]
        lines.append(f"{tier} & {meth} & {d['solved']}/{d['n']} & {d['par2_s']:.1f} & {gap} & {mem} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "summary.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tab_incremental(rows) -> None:
    """Giam dan vs chia doi, nhieu lan vs incremental, tren cac bai nho (kiem chung vai tro cua incremental)."""
    cols = [("descent", "cadical153", "Multi-SAT descent"), ("binary", "cadical153", "Multi-SAT bisect"),
            ("inc_descent", "cadical153", "Inc. SAT descent"), ("inc_binary", "cadical153", "Inc. SAT bisect")]
    names = [n for n in an.TIER_ORDER["small"] if n != "la05" and all((n, m, s) in rows for m, s, _ in cols)]
    lines = [r"\begin{tabular}{lr" + "r" * len(cols) + "}", r"\toprule",
             "Instance & Opt. & " + " & ".join(c[2] for c in cols) + r" \\", r"\midrule"]
    for n in names:
        rs = [rows[(n, m, s)] for m, s, _ in cols]
        best = min(r.time for r in rs)
        cs = [(r"\textbf{" + f"{r.time:.1f}" + "}") if r.time == best else f"{r.time:.1f}" for r in rs]
        lines.append(f"{esc(n)} & {rs[0].ub} & " + " & ".join(cs) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "incremental.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tab_hybrid(rows) -> None:
    cols = [("inc_binary", "cadical153", "Inc. SAT"), ("cpsat", "cpsat-w1", "CP-SAT"),
            ("hybrid_B", "cadical153+cpsat-w1", "Hybrid B"), ("hybrid_C", "cadical153+cpsat-w1", "Hybrid C")]
    names = [n for n in ("la21", "orb01", "abz7", "abz8", "abz9", "yn1") if (n, "hybrid_C", cols[-1][1]) in rows]
    lines = [r"\begin{tabular}{l" + "r" * len(cols) + "}", r"\toprule",
             "Instance & " + " & ".join(c[2] for c in cols) + r" \\", r"\midrule"]
    for n in names:
        lines.append(esc(n) + " & " + " & ".join(cell(rows.get((n, m, s))) for m, s, _ in cols) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "hybrid.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_wrappers() -> None:
    """Moi bang co mot file *_wrap.tex (table + caption + label) de main.tex chi viec \\input."""
    spec = {
        "main": ("tab:main", True,
                 "Results on all non-trivial instances. A number is the time (s) to a proven optimum; "
                 "$[\\mathrm{LB},\\mathrm{UB}]$ is the proven interval at the time limit; bold marks the best method "
                 "(fastest proof, otherwise best interval); -- means not run. Limits: 600\\,s (ft06--ft10), 900\\,s "
                 "(la11--orb01), 3600\\,s (abz7--yn1). Single run, one thread."),
        "summary": ("tab:summary", False,
                    "Per tier: instances solved, PAR2 (unsolved counted as twice the limit), mean relative gap "
                    "$(\\mathrm{UB}-\\mathrm{LB})/\\mathrm{LB}$ over unsolved runs, and mean peak memory."),
        "incremental": ("tab:inc", False,
                        "Time (s) of the four SAT search variants on small instances (CaDiCaL, bold = fastest)."),
        "hybrid": ("tab:hybrid", False,
                   "Hybrid CP-SAT $+$ SAT against its components on instances not solved by the plain SAT search "
                   "(time in s if proven optimal, otherwise the proven interval)."),
    }
    for name, (label, wide, cap) in spec.items():
        body = (TAB / f"{name}.tex").read_text(encoding="utf-8")
        inner = ("\\resizebox{\\textwidth}{!}{%\n" + body + "}") if wide else body
        txt = ("\\begin{table}[t]\n\\centering\n\\small\n" + inner +
               f"\\caption{{{cap}}}\\label{{{label}}}\n\\end{{table}}\n")
        (TAB / f"{name}_wrap.tex").write_text(txt, encoding="utf-8")


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    rows, _ = an.load_rows(SUMMARY)
    apply_style()
    fig_cactus(rows)
    fig_large_bounds(rows)
    fig_times(rows)
    tab_main(rows)
    tab_summary(rows)
    tab_incremental(rows)
    tab_hybrid(rows)
    write_wrappers()
    print("Da ghi:", *sorted(p.name for p in list(FIG.glob("*.pdf")) + list(TAB.glob("*.tex"))))


if __name__ == "__main__":
    main()
