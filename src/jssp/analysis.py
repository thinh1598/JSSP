"""Gop ket qua thi nghiem (results/raw/summary.csv) thanh bang so sanh, so lieu cho bao cao, va KIEM TRA NHAT QUAN.

Nguyen tac:
- Moi o (bai x cach x cau hinh solver) chi lay dong MOI NHAT trong summary.csv (chay lai bang --force se thay dong cu).
- Bang chinh chi gom cac cau hinh 1 luong (cong bang): inc_binary, binary (CaDiCaL), cpsat-w1, gurobi-t1, cpo-w1, cplex-t1.
  Cac dong con lai (descent, hybrid, nhieu luong...) vao bang phu.
- Bai tam thuong (heuristic da cham can duoi: lb_init >= ub_init) KHONG tinh vao so sanh solver.
- Chi dung thu vien chuan; ve hinh (matplotlib) la tuy chon.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

MAIN_COLS: List[Tuple[str, str]] = [            # (method, solver) -> cot cua bang chinh
    ("inc_binary", "cadical153"), ("binary", "cadical153"), ("cpsat", "cpsat-w1"),
    ("gurobi", "gurobi-t1"), ("cpo", "cpo-w1"), ("cplex", "cplex-t1")]
EXTRA_COLS: List[Tuple[str, str]] = [
    ("descent", "cadical153"), ("inc_descent", "cadical153"),
    ("hybrid_B", "cadical153+cpsat-w1"), ("hybrid_C", "cadical153+cpsat-w1")]
LABEL = {"inc_binary": "Inc. SAT", "binary": "SAT (chia doi)", "cpsat": "CP-SAT", "gurobi": "Gurobi MIP",
         "cpo": "CP Optimizer", "cplex": "CPLEX MIP", "descent": "SAT giam dan", "inc_descent": "Inc. SAT giam dan",
         "hybrid_B": "Hybrid B", "hybrid_C": "Hybrid C"}
TIER_BUDGET = {"small": 600, "medium": 900, "large": 3600}
TIER_ORDER = {"small": ["ft06", "la01", "la02", "la03", "la04", "la05", "ft10"],
              "medium": ["la06", "la11", "la16", "la21", "abz5", "abz6", "orb01"],
              "large": ["abz7", "abz8", "abz9", "yn1", "yn2", "yn3", "yn4"]}
SLACK = 1.10                                     # tong thoi gian > 110% ngan sach -> nghi may ngu


@dataclass
class Row:
    instance: str
    n_jobs: int
    n_machines: int
    method: str
    solver: str
    lb_init: int
    ub_init: int
    lb: int
    ub: int
    optimal: bool
    status: str
    n_calls: int
    time: float
    mem: Optional[float]
    timestamp: str

    @property
    def key(self) -> Tuple[str, str, str]:
        return (self.instance, self.method, self.solver)

    @property
    def trivial(self) -> bool:
        return self.lb_init >= self.ub_init


def tier_of(instance: str) -> Optional[str]:
    for t, names in TIER_ORDER.items():
        if instance in names:
            return t
    return None


def budget_of(instance: str) -> Optional[int]:
    t = tier_of(instance)
    return TIER_BUDGET[t] if t else None


def load_rows(path) -> Tuple[Dict[Tuple[str, str, str], Row], int]:
    """Doc summary.csv, giu dong MOI NHAT cua moi o (dong sau trong file thang). Tra ve (rows, so dong bi thay)."""
    latest: Dict[Tuple[str, str, str], Row] = {}
    replaced = 0
    with open(path, newline="", encoding="utf-8") as fh:
        for d in csv.DictReader(fh):
            if not d.get("instance"):
                continue
            r = Row(d["instance"], int(d["n_jobs"]), int(d["n_machines"]), d["method"], d["solver"],
                    int(d["lb_init"]), int(d["ub_init"]), int(d["lb_final"]), int(d["ub_final"]),
                    str(d["optimal"]).strip().lower() == "true", d["status"], int(d["n_calls"] or 0),
                    float(d["total_time"]), float(d["max_peak_mem_mb"]) if d.get("max_peak_mem_mb") else None,
                    d["timestamp"])
            if r.key in latest:
                replaced += 1
            latest[r.key] = r
    return latest, replaced


def load_known(path) -> Dict[str, Tuple[int, int, str]]:
    out = {}
    if path and Path(path).exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for d in csv.DictReader(fh):
                out[d["instance"]] = (int(d["lb"]), int(d["ub"]), d["status"])
    return out


def instance_order(rows: Iterable[Row]) -> List[str]:
    names = sorted({r.instance for r in rows})
    base = [n for t in ("small", "medium", "large") for n in TIER_ORDER[t] if n in names]
    return base + [n for n in names if n not in base]


# ---------------------------------------------------------------- bang so sanh
def cell_text(r: Optional[Row]) -> str:
    if r is None:
        return "-"
    if r.optimal:
        return f"{r.time:.1f}"
    if r.status == "TIMEOUT":
        return f"[{r.lb}, {r.ub}]"
    return {"MEMOUT": "het RAM", "ERROR": "loi"}.get(r.status, r.status)


def winner(cells: Dict[Tuple[str, str], Row]) -> Optional[Tuple[str, str]]:
    """Cach 'thang' tren mot bai: neu co cach chung minh toi uu thi cach nhanh nhat; neu khong, cach co
    can tren nho nhat, hoa thi can duoi lon nhat. Hoa chinh xac khong in dam."""
    if not cells:
        return None
    opt = {k: r for k, r in cells.items() if r.optimal}
    if opt:
        best = min(r.time for r in opt.values())
        w = [k for k, r in opt.items() if r.time == best]
    else:
        key = {k: (r.ub, -r.lb) for k, r in cells.items()}
        best = min(key.values())
        w = [k for k, v in key.items() if v == best]
    return w[0] if len(w) == 1 else None


def comparison_table(rows: Dict[Tuple[str, str, str], Row], cols: Sequence[Tuple[str, str]]) -> List[List[str]]:
    """Ma tran chu: dong tieu de + moi bai 1 dong. Cot: bai, co, cac cach. (Chua in dam.)"""
    names = [n for n in instance_order(rows.values()) if any((n, m, s) in rows for m, s in cols)]
    table = [["bai", "co"] + [LABEL[m] for m, _ in cols]]
    for n in names:
        sample = next(r for r in rows.values() if r.instance == n)
        table.append([n, f"{sample.n_jobs}x{sample.n_machines}"] + [cell_text(rows.get((n, m, s))) for m, s in cols])
    return table


def _bold_flags(rows, cols, names) -> Dict[Tuple[str, int], bool]:
    flags = {}
    for n in names:
        cells = {(m, s): rows[(n, m, s)] for m, s in cols if (n, m, s) in rows}
        sample = next((r for r in cells.values()), None)
        if sample is None or sample.trivial:
            continue
        w = winner(cells)
        if w is not None:
            flags[(n, [c for c in cols].index(w))] = True
    return flags


def to_markdown(table: List[List[str]], bold: Optional[Dict[Tuple[str, int], bool]] = None) -> str:
    bold = bold or {}
    out = ["| " + " | ".join(table[0]) + " |", "|" + "---|" * len(table[0])]
    for row in table[1:]:
        cells = [(f"**{c}**" if bold.get((row[0], j - 2)) else c) for j, c in enumerate(row)]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def to_latex(table: List[List[str]], bold: Optional[Dict[Tuple[str, int], bool]] = None, caption: str = "",
             label: str = "") -> str:
    bold = bold or {}

    def esc(s: str) -> str:
        return s.replace("_", r"\_").replace("%", r"\%").replace("&", r"\&").replace("[", "{[}").replace("]", "{]}")

    n = len(table[0])
    lines = [r"\begin{table}[t]", r"\centering", r"\small",
             r"\begin{tabular}{ll" + "r" * (n - 2) + "}", r"\toprule",
             " & ".join(esc(c) for c in table[0]) + r" \\", r"\midrule"]
    for row in table[1:]:
        cells = [esc(c) for c in row]
        for j in range(2, n):
            if bold.get((row[0], j - 2)):
                cells[j] = r"\textbf{" + cells[j] + "}"
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    if caption:
        lines.append(rf"\caption{{{caption}}}")
    if label:
        lines.append(rf"\label{{{label}}}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- tong hop theo cach
def summary_by_method(rows: Dict[Tuple[str, str, str], Row], cols: Sequence[Tuple[str, str]]) -> List[Dict]:
    """Theo bac: so bai giai xong / so bai (khong tinh bai tam thuong), PAR2 (giay; bai khong giai xong tinh 2x ngan sach),
    khoang cach tuong doi trung binh (ub-lb)/lb cua cac bai het gio, RAM dinh trung binh."""
    out = []
    for tier, names in TIER_ORDER.items():
        budget = TIER_BUDGET[tier]
        for m, s in cols:
            rs = [rows[(n, m, s)] for n in names if (n, m, s) in rows and not rows[(n, m, s)].trivial]
            if not rs:
                continue
            solved = [r for r in rs if r.optimal]
            unsolved = [r for r in rs if not r.optimal]
            par2 = sum(r.time if r.optimal else 2 * budget for r in rs) / len(rs)
            gaps = [100.0 * (r.ub - r.lb) / r.lb for r in unsolved if r.lb > 0]
            mems = [r.mem for r in rs if r.mem is not None]
            out.append({"tier": tier, "budget_s": budget, "method": LABEL[m], "n": len(rs), "solved": len(solved),
                        "par2_s": round(par2, 1), "mean_gap_unsolved_pct": round(sum(gaps) / len(gaps), 2) if gaps else "",
                        "mean_peak_mem_mb": round(sum(mems) / len(mems), 0) if mems else ""})
    return out


def best_bounds(rows: Dict[Tuple[str, str, str], Row]) -> List[Dict]:
    """Moi bai: can duoi tot nhat, can tren tot nhat (cach nao dat duoc), da chung minh toi uu chua, cach nao chung minh nhanh nhat."""
    out = []
    for n in instance_order(rows.values()):
        rs = [r for r in rows.values() if r.instance == n]
        opts = [r for r in rs if r.optimal]
        fastest = min(opts, key=lambda r: r.time) if opts else None
        best_lb, best_ub = max(r.lb for r in rs), min(r.ub for r in rs)
        who = lambda pick: " / ".join(sorted({LABEL.get(r.method, r.method) for r in rs if pick(r)}))   # noqa: E731
        out.append({"instance": n, "size": f"{rs[0].n_jobs}x{rs[0].n_machines}", "best_lb": best_lb,
                    "best_lb_by": "(da toi uu)" if opts else who(lambda r: r.lb == best_lb), "best_ub": best_ub,
                    "best_ub_by": "(da toi uu)" if opts else who(lambda r: r.ub == best_ub), "proven_optimal": bool(opts),
                    "fastest_proof": f"{LABEL.get(fastest.method, fastest.method)} {fastest.time:.1f}s" if fastest else ""})
    return out


# ---------------------------------------------------------------- kiem tra nhat quan
def check_consistency(rows: Dict[Tuple[str, str, str], Row], known: Optional[Dict] = None) -> List[Tuple[str, str]]:
    """Tra ve danh sach (muc, thong bao). Muc 'LOI' = ket qua mau thuan nhau (nghi co loi code / mo hinh);
    'CANH BAO' = dong nen xem lai (vd may ngu, 0 lan goi) hoac so tay tu van hien chua kiem chung."""
    msgs: List[Tuple[str, str]] = []
    known = known or {}
    by_inst: Dict[str, List[Row]] = defaultdict(list)
    for r in rows.values():
        by_inst[r.instance].append(r)
    for n, rs in by_inst.items():
        for r in rs:
            if r.lb > r.ub:
                msgs.append(("LOI", f"{n}/{r.method}/{r.solver}: can duoi {r.lb} > can tren {r.ub}"))
            if r.optimal and r.lb != r.ub:
                msgs.append(("LOI", f"{n}/{r.method}/{r.solver}: danh dau toi uu nhung LB={r.lb} != UB={r.ub}"))
        best_lb, best_ub = max(r.lb for r in rs), min(r.ub for r in rs)
        if best_lb > best_ub:
            who_l = max(rs, key=lambda r: r.lb)
            who_u = min(rs, key=lambda r: r.ub)
            msgs.append(("LOI", f"{n}: can duoi tot nhat {best_lb} ({who_l.method}) > can tren tot nhat {best_ub} "
                                f"({who_u.method}): hai ket qua khong the cung dung"))
        opt_vals = {r.ub for r in rs if r.optimal}
        if len(opt_vals) > 1:
            msgs.append(("LOI", f"{n}: cac cach 'toi uu' cho gia tri khac nhau: {sorted(opt_vals)}"))
        if n in known:
            klb, kub, kst = known[n]
            tag = "" if kst == "optimal" else " (bai con mo trong tai lieu)"
            if best_ub < klb:
                msgs.append(("LOI", f"{n}: cap tren {best_ub} thap hon can duoi trong tai lieu {klb}{tag}"))
            if kst == "optimal" and best_lb > kub:
                msgs.append(("LOI", f"{n}: can duoi {best_lb} vuot toi uu trong tai lieu {kub}"))
            if kst == "optimal" and opt_vals and opt_vals != {kub}:
                msgs.append(("LOI", f"{n}: toi uu cua ta {sorted(opt_vals)} khac so trong tai lieu {kub}"))
        b = budget_of(n)
        for r in rs:
            if b and r.time > SLACK * (b + 60) and not r.trivial:
                msgs.append(("CANH BAO", f"{n}/{r.method}/{r.solver}: chay {r.time:.0f}s, vuot ngan sach {b}s "
                                         f"(may ngu? nen chay lai bang --force)"))
            if b and r.status == "TIMEOUT" and r.time < 0.9 * b and not r.trivial:
                msgs.append(("CANH BAO", f"{n}/{r.method}/{r.solver}: het gio sau {r.time:.0f}s, it hon nhieu so voi ngan sach "
                                         f"{b}s (lan chay thu gioi han ngan? nen chay lai bang --force)"))
            if r.n_calls == 0 and not r.trivial and r.method in ("cpsat", "gurobi", "cpo", "cplex"):
                msgs.append(("CANH BAO", f"{n}/{r.method}/{r.solver}: 0 lan goi solver (khong phai bai tam thuong)"))
            if r.status in ("ERROR", "MEMOUT"):
                msgs.append(("CANH BAO", f"{n}/{r.method}/{r.solver}: trang thai {r.status}"))
    msgs.sort(key=lambda m: (m[0] != "LOI", m[1]))
    return msgs


def cactus_data(rows: Dict[Tuple[str, str, str], Row], cols: Sequence[Tuple[str, str]]) -> List[Dict]:
    """Du lieu ve 'cactus plot': voi moi cach, thoi gian cua cac bai GIAI XONG (khong tam thuong), xep tang dan."""
    out = []
    for m, s in cols:
        ts = sorted(r.time for r in rows.values() if r.method == m and r.solver == s and r.optimal and not r.trivial)
        for k, t in enumerate(ts, 1):
            out.append({"method": LABEL[m], "solved": k, "time_s": round(t, 2)})
    return out
