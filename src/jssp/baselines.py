"""Khung chay BASELINE (hien co: CP-SAT) theo cung quy cach voi SAT nhieu lan / Incremental:
tien trinh rieng co gioi han gio va RAM, kiem tra lai lich o tien trinh cha, ghi cung file summary.csv.

Quy doi trang thai ve cung tu vung voi search_multi:
  OPTIMAL  : solver chung minh toi uu (lb == ub)
  TIMEOUT  : het gio; van bao khoang [lb, ub] da co (ub = lich tot nhat, lb = can duoi cua solver)
  MEMOUT   : vuot gioi han RAM;  ERROR: loi / lich tra ve khong hop le
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Optional

from .heuristic import best_greedy
from .instance import read_instance
from .runner import CsvLog, run_with_limits
from .search_multi import ROOT, SUMMARY_FIELDS, SearchResult
from .validate import makespan, validate_schedule

RUN_CPSAT = ROOT / "scripts" / "run_cpsat.py"


def run_cpsat(path, time_limit: float = 600, workers: int = 1, seed: int = 0,
              mem_limit_mb: Optional[float] = None, summary_log: Optional[CsvLog] = None,
              save_dir: Optional[Path] = None, verbose: bool = True) -> SearchResult:
    path = Path(path)
    inst = read_instance(path)
    t_start = time.perf_counter()
    lb0 = inst.trivial_lower_bound()
    starts0 = best_greedy(inst)                      # cung thong tin ban dau nhu huong SAT
    ub0 = makespan(inst, starts0)
    solver_name = f"cpsat-w{workers}"
    lb, ub, starts, status, optimal = lb0, ub0, starts0, "ERROR", False
    peak = None
    called = False

    if lb0 >= ub0:                                   # heuristic cham can duoi: toi uu ngay, khong can goi solver
        status, optimal, lb = "OPTIMAL", True, ub0
    else:
        cmd = [sys.executable, str(RUN_CPSAT), str(path), "--time-limit", str(time_limit),
               "--workers", str(workers), "--seed", str(seed), "--lb", str(lb0), "--ub", str(ub0)]
        info = run_with_limits(cmd, timeout=time_limit + 60, mem_limit_mb=mem_limit_mb)
        called = True
        peak = None if info.peak_mem_mb is None else round(info.peak_mem_mb, 1)
        d = None
        if info.status == "OK" and info.returncode == 0 and info.stdout.strip():
            try:
                d = json.loads(info.stdout.strip().splitlines()[-1])
            except ValueError:
                d = None
        if info.status != "OK":
            status = info.status                      # TIMEOUT | MEMOUT: giu [lb0, ub0] va lich heuristic
        elif d is None:
            status = "ERROR"
            if verbose:
                print("CP-SAT loi:", (info.stderr or info.stdout).strip()[-500:])
        else:
            st = d.get("status")
            bound = d.get("best_bound")
            lb_solver = lb0 if bound is None else max(lb0, math.ceil(bound - 1e-6))
            if st in ("OPTIMAL", "FEASIBLE"):
                s = d.get("starts")
                if s and not validate_schedule(inst, s, ub0):         # khong tin tien trinh con
                    starts, ub = s, makespan(inst, s)
                    if st == "OPTIMAL":
                        status, optimal, lb = "OPTIMAL", True, ub
                    else:
                        status, lb = "TIMEOUT", min(lb_solver, ub)
                else:
                    status = "ERROR"
            elif st == "UNKNOWN":                      # het gio, chua tim duoc loi giai tot hon heuristic
                status, lb = "TIMEOUT", min(lb_solver, ub0)
            else:
                status = "ERROR"                       # INFEASIBLE / MODEL_INVALID: khong nen xay ra voi ub hop le

    total = time.perf_counter() - t_start
    res = SearchResult(inst.name, "cpsat", solver_name, lb, ub, optimal, status, 1 if called else 0,
                       total, starts, [])
    if verbose:
        print(f"[cpsat] {inst.name}: {status}  LB={lb} UB={ub}  {total:.1f}s"
              + (f"  {peak:.0f}MB" if peak is not None else ""))
    if summary_log:
        summary_log.append({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "instance": inst.name,
                            "n_jobs": inst.n_jobs, "n_machines": inst.n_machines, "method": "cpsat",
                            "solver": solver_name, "lb_init": lb0, "lb_source": "don gian (max job, max tai may)",
                            "ub_init": ub0, "ub_source": "heuristic (co lich kem theo)", "lb_final": lb,
                            "ub_final": ub, "optimal": optimal, "status": status, "n_calls": res.n_calls,
                            "total_time": round(total, 2), "max_peak_mem_mb": "" if peak is None else peak})
    if save_dir and starts:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / f"{inst.name}_cpsat_{solver_name}.json").write_text(
            json.dumps({"instance": inst.name, "makespan": ub, "optimal": optimal, "lb": lb, "starts": starts}),
            encoding="utf-8")
    return res
