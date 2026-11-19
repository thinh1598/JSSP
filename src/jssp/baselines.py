"""Khung chay BASELINE (CP-SAT, Gurobi MIP) theo cung quy cach voi SAT nhieu lan / Incremental:
tien trinh rieng co gioi han gio va RAM, kiem tra lai lich o tien trinh cha, ghi cung file summary.csv.

Quy doi trang thai ve cung tu vung voi search_multi:
  OPTIMAL  : solver chung minh toi uu (lb == ub)
  TIMEOUT  : het gio; van bao khoang [lb, ub] da co (ub = lich tot nhat, lb = can duoi cua solver)
  MEMOUT   : vuot gioi han RAM;  ERROR: loi / lich tra ve khong hop le
  NOT_INSTALLED | NO_LICENSE | LICENSE_LIMIT : (Gurobi) thieu thu vien / giay phep -> in thong bao, KHONG ghi dong nao
  vao summary.csv (de khong lam ban ket qua thi nghiem; sua xong chay lai la xong)
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
RUN_GUROBI = ROOT / "scripts" / "run_gurobi.py"
RUN_CPO = ROOT / "scripts" / "run_cpo.py"
RUN_CPLEX = ROOT / "scripts" / "run_cplex.py"

LICENSE_STATUSES = ("NOT_INSTALLED", "NO_LICENSE", "LICENSE_LIMIT")
LICENSE_HELP = {
    ("gurobi", "NOT_INSTALLED"): "Chua cai gurobipy.  Chay:  python -m pip install gurobipy",
    ("gurobi", "NO_LICENSE"): "Khong tim thay giay phep Gurobi hop le (gurobi.lic). Chay lai grbgetkey / kiem tra GRB_LICENSE_FILE.",
    ("gurobi", "LICENSE_LIMIT"): "Mo hinh vuot gioi han cua giay phep gioi han kich thuoc (2000 bien / 2000 rang buoc). "
                                 "Can giay phep day du (academic) cho bai nay.",
    ("cpo", "NOT_INSTALLED"): "Chua cai docplex.  Chay:  python -m pip install docplex  (can ca CPLEX Optimization Studio).",
    ("cpo", "LICENSE_LIMIT"): "CP Optimizer bi gioi han ban community. Can CPLEX Optimization Studio day du (cpoptimizer.exe).",
    ("cplex", "NOT_INSTALLED"): "Khong thay cplex.exe. Cai CPLEX Optimization Studio, hoac dat bien JSSP_CPLEX_EXE.",
    ("cplex", "LICENSE_LIMIT"): "cplex.exe bi gioi han ban community (loi 1016). Can CPLEX Optimization Studio day du.",
}


def license_help(method: str, status: str) -> str:
    return LICENSE_HELP.get((method, status), f"Van de giay phep / cai dat ({status}).")


def _run_external(path, *, method: str, solver_name: str, script, extra_args, time_limit: float,
                  mem_limit_mb: Optional[float], summary_log: Optional[CsvLog], save_dir: Optional[Path],
                  verbose: bool, bound_tol: float, pretty: str) -> SearchResult:
    """Chay mot baseline trong tien trinh con (script in 1 dong JSON), kiem tra lai lich, ghi summary.csv."""
    path = Path(path)
    inst = read_instance(path)
    t_start = time.perf_counter()
    lb0 = inst.trivial_lower_bound()
    starts0 = best_greedy(inst)                      # cung thong tin ban dau nhu huong SAT
    ub0 = makespan(inst, starts0)
    lb, ub, starts, status, optimal = lb0, ub0, starts0, "ERROR", False
    peak = None
    called = False

    if lb0 >= ub0:                                   # heuristic cham can duoi: toi uu ngay, khong can goi solver
        status, optimal, lb = "OPTIMAL", True, ub0
    else:
        cmd = [sys.executable, str(script), str(path), "--time-limit", str(time_limit), *map(str, extra_args),
               "--lb", str(lb0), "--ub", str(ub0)]
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
                print(f"{pretty} loi:", (info.stderr or info.stdout).strip()[-500:])
        else:
            st = d.get("status")
            bound = d.get("best_bound")
            lb_solver = lb0 if bound is None else max(lb0, math.ceil(bound - bound_tol))
            if st in LICENSE_STATUSES:
                status = st                            # khong phai ket qua thi nghiem: khong ghi gi ca
            elif st in ("OPTIMAL", "FEASIBLE"):
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
                if verbose and d.get("message"):
                    print(f"{pretty} loi:", d["message"])

    total = time.perf_counter() - t_start
    res = SearchResult(inst.name, method, solver_name, lb, ub, optimal, status, 1 if called else 0,
                       total, starts, [], peak)
    if status in LICENSE_STATUSES:
        print(f"[{method}] {inst.name}: {status} - {license_help(method, status)}")
        return res
    if verbose:
        print(f"[{method}] {inst.name}: {status}  LB={lb} UB={ub}  {total:.1f}s"
              + (f"  {peak:.0f}MB" if peak is not None else ""))
    if summary_log:
        summary_log.append({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "instance": inst.name,
                            "n_jobs": inst.n_jobs, "n_machines": inst.n_machines, "method": method,
                            "solver": solver_name, "lb_init": lb0, "lb_source": "don gian (max job, max tai may)",
                            "ub_init": ub0, "ub_source": "heuristic (co lich kem theo)", "lb_final": lb,
                            "ub_final": ub, "optimal": optimal, "status": status, "n_calls": res.n_calls,
                            "total_time": round(total, 2), "max_peak_mem_mb": "" if peak is None else peak})
    if save_dir and starts:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / f"{inst.name}_{method}_{solver_name}.json").write_text(
            json.dumps({"instance": inst.name, "makespan": ub, "optimal": optimal, "lb": lb, "starts": starts}),
            encoding="utf-8")
    return res


def run_cpsat(path, time_limit: float = 600, workers: int = 1, seed: int = 0,
              mem_limit_mb: Optional[float] = None, summary_log: Optional[CsvLog] = None,
              save_dir: Optional[Path] = None, verbose: bool = True) -> SearchResult:
    return _run_external(path, method="cpsat", solver_name=f"cpsat-w{workers}", script=RUN_CPSAT,
                         extra_args=["--workers", workers, "--seed", seed], time_limit=time_limit,
                         mem_limit_mb=mem_limit_mb, summary_log=summary_log, save_dir=save_dir, verbose=verbose,
                         bound_tol=1e-6, pretty="CP-SAT")


def run_gurobi(path, time_limit: float = 600, threads: int = 1, seed: int = 0,
               mem_limit_mb: Optional[float] = None, summary_log: Optional[CsvLog] = None,
               save_dir: Optional[Path] = None, verbose: bool = True) -> SearchResult:
    """Gurobi MIP. Can bien (bound) cua Gurobi co sai so ~1e-5 nen lam tron lenh tran voi dung sai 1e-4."""
    return _run_external(path, method="gurobi", solver_name=f"gurobi-t{threads}", script=RUN_GUROBI,
                         extra_args=["--threads", threads, "--seed", seed], time_limit=time_limit,
                         mem_limit_mb=mem_limit_mb, summary_log=summary_log, save_dir=save_dir, verbose=verbose,
                         bound_tol=1e-4, pretty="Gurobi")


def run_cpo(path, time_limit: float = 600, workers: int = 1, seed: int = 0,
            mem_limit_mb: Optional[float] = None, summary_log: Optional[CsvLog] = None,
            save_dir: Optional[Path] = None, verbose: bool = True) -> SearchResult:
    """CPLEX CP Optimizer (docplex.cp + cpoptimizer.exe)."""
    return _run_external(path, method="cpo", solver_name=f"cpo-w{workers}", script=RUN_CPO,
                         extra_args=["--workers", workers, "--seed", seed], time_limit=time_limit,
                         mem_limit_mb=mem_limit_mb, summary_log=summary_log, save_dir=save_dir, verbose=verbose,
                         bound_tol=1e-4, pretty="CP Optimizer")


def run_cplex(path, time_limit: float = 600, threads: int = 1, seed: int = 0,
              mem_limit_mb: Optional[float] = None, summary_log: Optional[CsvLog] = None,
              save_dir: Optional[Path] = None, verbose: bool = True) -> SearchResult:
    """CPLEX MIP (cong thuc big-M cua mip.py, qua cplex.exe)."""
    return _run_external(path, method="cplex", solver_name=f"cplex-t{threads}", script=RUN_CPLEX,
                         extra_args=["--threads", threads, "--seed", seed], time_limit=time_limit,
                         mem_limit_mb=mem_limit_mb, summary_log=summary_log, save_dir=save_dir, verbose=verbose,
                         bound_tol=1e-4, pretty="CPLEX MIP")
