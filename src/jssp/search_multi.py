"""SAT NHIEU LAN: tim makespan toi uu bang cach giai nhieu cong thuc S_L, moi lan sinh CNF moi.

Hai cach chon L tiep theo (moi lan goi la mot lan giai S_L doc lap, trong tien trinh rieng co timeout):

  descent (giam dan):  L = UB-1.  SAT -> UB = makespan cua lich tim duoc (<= L), thu tiep L = UB-1.
                       UNSAT -> UB chinh la toi uu.
  binary  (chia doi):  giu [lo, hi]; hi la makespan DA CO lich, lo la can duoi DA CHUNG MINH.
                       mid = (lo+hi)//2. SAT -> hi = makespan tim duoc. UNSAT -> lo = mid+1. Dung khi lo == hi.

Bat bien: moi lich dung de cap nhat UB deu duoc kiem tra lai bang validate_schedule o tien trinh cha.
Neu bi dung giua chung (timeout/het RAM) ta van co khoang [lo, hi] da chung minh, giong Bang 5 cua bai bao.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .heuristic import best_greedy
from .instance import JSSPInstance, read_instance
from .runner import CsvLog, run_with_limits
from .validate import makespan, validate_schedule

ROOT = Path(__file__).resolve().parents[2]
RUN_SAT = ROOT / "scripts" / "run_sat.py"

CALL_FIELDS = ["timestamp", "instance", "method", "solver", "call_idx", "L", "status", "makespan", "valid",
               "vars", "clauses", "encode_time", "solve_time", "wall_time", "peak_mem_mb", "lb_after", "ub_after"]
SUMMARY_FIELDS = ["timestamp", "instance", "n_jobs", "n_machines", "method", "solver", "lb_init", "lb_source",
                  "ub_init", "ub_source", "lb_final", "ub_final", "optimal", "status", "n_calls",
                  "total_time", "max_peak_mem_mb"]


def resolve_instance(name_or_path: str) -> Path:
    """'ft10' -> data/ft10.txt hoac data/instances/ft10.txt ; hoac duong dan file."""
    p = Path(name_or_path)
    if p.exists():
        return p
    for cand in (ROOT / "data" / f"{name_or_path}.txt", ROOT / "data" / "instances" / f"{name_or_path}.txt"):
        if cand.exists():
            return cand
    raise FileNotFoundError(f"khong tim thay bai '{name_or_path}' (chay scripts/fetch_benchmarks.py?)")


@dataclass
class SearchResult:
    instance: str
    method: str
    solver: str
    lb: int                      # can duoi DA CHUNG MINH (hoac lay tu can duoi don gian / tham so --lb)
    ub: int                      # makespan cua lich tot nhat DA CO
    optimal: bool
    status: str                  # OPTIMAL | TIMEOUT | MEMOUT | ERROR | UB_INVALID
    n_calls: int
    total_time: float
    best_starts: Optional[List[List[int]]]
    calls: List[Dict] = field(default_factory=list)


def _call(path: Path, L: int, solver: str, tiny: bool, timeout: float, mem_limit_mb: Optional[float]) -> Dict:
    cmd = [sys.executable, str(RUN_SAT), str(path), "--L", str(L), "--solver", solver, "--json"]
    if tiny:
        cmd.append("--tiny")
    info = run_with_limits(cmd, timeout=timeout, mem_limit_mb=mem_limit_mb)
    d: Dict = {"L": L, "wall_time": round(info.wall, 3),
               "peak_mem_mb": None if info.peak_mem_mb is None else round(info.peak_mem_mb, 1)}
    if info.status != "OK":
        d["status"] = info.status
    elif info.returncode != 0 or not info.stdout.strip():
        d["status"] = "ERROR"
        d["detail"] = (info.stderr or info.stdout).strip()[-500:]
    else:
        d.update(json.loads(info.stdout.strip().splitlines()[-1]))
    return d


def search(path, method: str = "binary", solver: str = "cadical153", lb: Optional[int] = None,
           ub: Optional[int] = None, per_call_timeout: float = 600, total_timeout: float = 3600,
           mem_limit_mb: Optional[float] = None, tiny: bool = False, calls_log: Optional[CsvLog] = None,
           summary_log: Optional[CsvLog] = None, save_dir: Optional[Path] = None,
           verbose: bool = True) -> SearchResult:
    if method not in ("descent", "binary"):
        raise ValueError("method phai la 'descent' hoac 'binary'")
    path = Path(path)
    inst: JSSPInstance = read_instance(path)
    t_start = time.perf_counter()
    calls: List[Dict] = []
    state = {"lo": lb if lb is not None else inst.trivial_lower_bound(), "hi": None, "starts": None}
    lb_source = "tham so" if lb is not None else "don gian (max job, max tai may)"
    status = "OPTIMAL"

    def log_call(d: Dict) -> None:
        d.update(timestamp=time.strftime("%Y-%m-%d %H:%M:%S"), instance=inst.name, method=method,
                 solver="DPLL-tiny" if tiny else solver, call_idx=len(calls) + 1,
                 lb_after=state["lo"], ub_after=state["hi"])
        calls.append(d)
        if calls_log:
            calls_log.append(d)
        if verbose:
            mk = f" (makespan {d['makespan']})" if d.get("makespan") is not None else ""
            mem = f"  {d['peak_mem_mb']:.0f}MB" if d.get("peak_mem_mb") is not None else ""
            print(f"[{method}] goi {d['call_idx']}: L={d['L']} -> {d['status']}{mk}  {d['wall_time']:.1f}s{mem}"
                  f"   | LB={state['lo']} UB={state['hi']}", flush=True)

    def do_call(L: int) -> Dict:
        remain = total_timeout - (time.perf_counter() - t_start)
        if remain <= 0:
            d = {"L": L, "status": "TIMEOUT", "wall_time": 0.0}
        else:
            d = _call(path, L, solver, tiny, min(per_call_timeout, remain), mem_limit_mb)
        return d          # (ghi nhat ky SAU khi cap nhat LB/UB, xem log_call)

    def accept_schedule(d: Dict) -> bool:
        """Kiem tra lai lich o tien trinh cha (khong tin tien trinh con)."""
        starts = d.get("starts")
        if starts and not validate_schedule(inst, starts, d["L"]):
            state["hi"] = makespan(inst, starts)
            state["starts"] = starts
            return True
        return False

    # ---- can tren ban dau
    if ub is None:
        state["starts"] = best_greedy(inst)
        state["hi"] = makespan(inst, state["starts"])
        ub_source = "heuristic (co lich kem theo)"
    else:
        ub_source = "tham so (da xac nhan bang 1 lan giai)"
        state["hi"] = ub
        d = do_call(ub)
        if not (d["status"] == "SAT" and accept_schedule(d)):
            status = "UB_INVALID" if d["status"] == "UNSAT" else (d["status"] if d["status"] != "SAT" else "ERROR")
            state["hi"] = ub if status != "UB_INVALID" else None
        log_call(d)
    ub_init, lb_init = state["hi"], state["lo"]

    # ---- vong lap chinh
    while status == "OPTIMAL" and state["hi"] is not None and state["lo"] < state["hi"]:
        lo, hi = state["lo"], state["hi"]
        L = hi - 1 if method == "descent" else (lo + hi) // 2
        d = do_call(L)
        if d["status"] == "SAT":
            if not accept_schedule(d):
                status = "ERROR"
        elif d["status"] == "UNSAT":
            state["lo"] = hi if method == "descent" else L + 1
        else:
            status = d["status"]          # TIMEOUT | MEMOUT | ERROR
        log_call(d)                       # ghi nhat ky sau khi da cap nhat LB/UB

    total = time.perf_counter() - t_start
    optimal = status == "OPTIMAL" and state["hi"] is not None and state["lo"] == state["hi"]
    res = SearchResult(inst.name, method, "DPLL-tiny" if tiny else solver, state["lo"],
                       state["hi"] if state["hi"] is not None else -1, optimal, status, len(calls), total,
                       state["starts"], calls)
    peaks = [c["peak_mem_mb"] for c in calls if c.get("peak_mem_mb") is not None]
    if summary_log:
        summary_log.append({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "instance": inst.name,
                            "n_jobs": inst.n_jobs, "n_machines": inst.n_machines, "method": method,
                            "solver": res.solver, "lb_init": lb_init, "lb_source": lb_source, "ub_init": ub_init,
                            "ub_source": ub_source, "lb_final": res.lb, "ub_final": res.ub, "optimal": optimal,
                            "status": status, "n_calls": len(calls), "total_time": round(total, 2),
                            "max_peak_mem_mb": max(peaks) if peaks else ""})
    if save_dir and state["starts"]:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / f"{inst.name}_{method}_{res.solver}.json").write_text(
            json.dumps({"instance": inst.name, "makespan": res.ub, "optimal": optimal, "lb": res.lb,
                        "starts": state["starts"]}), encoding="utf-8")
    return res
