"""Baseline CPLEX MIP: cung cong thuc big-M voi Gurobi (mip.py), viet ra file .lp roi goi cplex.exe cua Studio.

Vi sao khong dung goi Python 'cplex' cai bang pip: do la ban community, gioi han ~1000 bien / 1000 rang buoc
(loi 1016), khong du cho bai trung/lon. cplex.exe cua Studio la ban day du (da kiem bang scripts/check_cplex.py).

Cung thong tin ban dau (lb, ub), 1 luong (threads=1), do thoi gian theo dong ho tuong (clocktype 2).
"""
from __future__ import annotations

import re
import tempfile
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .instance import JSSPInstance
from .mip import CMAX, MipSpec, build_mip
from .studio import find_exe


# ---------------------------------------------------------------- viet file .lp
CNAME = "mksp"                  # ten bien makespan trong file .lp (tranh ten 1 chu cai / tu khoa)


def _vname(node: tuple) -> str:
    return CNAME if node == CMAX else f"s_{node[0]}_{node[1]}"


def _yname(key: Tuple[tuple, tuple]) -> str:
    (a, b) = key
    return f"y_{a[0]}_{a[1]}_{b[0]}_{b[1]}"


def _wrap(terms: List[str], per_line: int = 8) -> List[str]:
    """Dinh dang LP gioi han do dai dong (~560 ky tu): ngat dong sau moi vai so hang."""
    out = []
    for i in range(0, len(terms), per_line):
        out.append("   " + " ".join(terms[i:i + per_line]))
    return out


def lp_text(spec: MipSpec) -> str:
    """Chuyen MipSpec thanh van ban dinh dang CPLEX LP.
    Moi rang buoc  s[x] - s[w] >= c + coef*y  thanh  s_x - s_w - coef*y >= c."""
    lines = ["\\ JSSP big-M MIP (sinh tu jssp.mip)", "Minimize", f" obj: {CNAME}", "Subject To"]
    for n, k in enumerate(spec.cons):
        terms = [_vname(k.x), "-", _vname(k.w)]
        if k.ykey is not None and k.coef != 0:
            terms += ["-" if k.coef > 0 else "+", str(abs(k.coef)), _yname(k.ykey)]
        lines.append(f" c{n}: " + " ".join(terms) + f" >= {k.c}")
    lines.append("Bounds")
    for a in spec.ops:
        lines.append(f" {spec.lo[a]} <= {_vname(a)} <= {spec.hi[a]}")
    lines.append(f" {spec.lo[CMAX]} <= {CNAME} <= {spec.hi[CMAX]}")
    lines.append("General")
    lines += _wrap([_vname(a) for a in spec.ops] + [CNAME])
    if spec.ykeys:
        lines.append("Binary")
        lines += _wrap([_yname(k) for k in spec.ykeys])
    lines.append("End")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- doc ket qua cua cplex.exe
FLOAT = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"


def parse_status(out: str, have_solution: bool) -> str:
    low = out.lower()
    if "problem size limits exceeded" in low or "error 1016" in low:
        return "LICENSE_LIMIT"
    if "integer optimal solution" in low or "integer optimal, tolerance" in low or "mip - optimal" in low:
        return "OPTIMAL"
    if re.search(r"mip - (integer )?infeasible", low) and not have_solution:
        return "INFEASIBLE"
    return "FEASIBLE" if have_solution else "UNKNOWN"        # het gio / het bo nho: co nghiem thi FEASIBLE


def parse_best_bound(out: str) -> Optional[float]:
    """Lay can duoi tot nhat tu nhat ky: dong 'Current MIP best bound = X (gap = ...)' (lay lan cuoi)."""
    hits = re.findall(r"best bound\s*=\s*(" + FLOAT + ")", out, flags=re.IGNORECASE)
    return float(hits[-1]) if hits else None


def parse_sol_values(xml_text: str) -> Dict[str, float]:
    """Doc file .sol (XML) cua CPLEX: <variable name="..." value="..."/>."""
    vals: Dict[str, float] = {}
    for m in re.finditer(r'<variable\b[^>]*?\bname="([^"]+)"[^>]*?\bvalue="(' + FLOAT + ')"', xml_text):
        vals[m.group(1)] = float(m.group(2))
    return vals


def solve_cplex_mip(inst: JSSPInstance, lb: int, ub: int, time_limit: float = 600.0, threads: int = 1,
                    seed: int = 0, workdir: Optional[Path] = None) -> Dict:
    """Tra ve dict: status, makespan, best_bound, starts, wall_time, threads, version.
    status: OPTIMAL | FEASIBLE | UNKNOWN | INFEASIBLE | NOT_INSTALLED | LICENSE_LIMIT."""
    t0 = time.perf_counter()
    exe = find_exe("cplex")
    if not exe:
        return {"status": "NOT_INSTALLED"}
    spec = build_mip(inst, lb, ub)
    work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="jssp_cplex_"))
    work.mkdir(parents=True, exist_ok=True)
    lp, sol = work / "model.lp", work / "model.sol"
    lp.write_text(lp_text(spec), encoding="ascii")
    if sol.exists():
        sol.unlink()
    script = "\n".join([
        "set clocktype 2",                              # dong ho tuong (khong phai thoi gian CPU)
        f"set timelimit {float(time_limit)}",
        f"set threads {int(threads)}",
        f"set randomseed {int(seed)}",
        "set mip tolerances mipgap 0",
        "set mip tolerances absmipgap 0",
        f"read {lp}",
        "optimize",
        f"write {sol}",
        "quit", ""])
    p = subprocess.run([exe], input=script, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    values = parse_sol_values(sol.read_text(encoding="utf-8", errors="replace")) if sol.exists() else {}
    have = bool(values) and all(_vname(a) in values for a in spec.ops)
    status = parse_status(out, have)
    starts: Optional[List[List[int]]] = None
    makespan: Optional[int] = None
    if have and status in ("OPTIMAL", "FEASIBLE"):
        starts = [[int(round(values[_vname((l, i))])) for i in range(len(job))] for l, job in enumerate(inst.jobs)]
        makespan = int(round(values.get(CNAME, max(starts[l][-1] + inst.jobs[l][-1][1] for l in range(inst.n_jobs)))))
    ver = re.search(r"Interactive Optimizer\s+([\d.]+)|Version Identifier:\s*([\d.]+)", out)
    return {"status": status, "makespan": makespan, "best_bound": parse_best_bound(out), "starts": starts,
            "wall_time": round(time.perf_counter() - t0, 3), "threads": int(threads),
            "version": (ver.group(1) or ver.group(2)) if ver else "?", "message": out.strip()[-300:] if status == "LICENSE_LIMIT" else ""}
