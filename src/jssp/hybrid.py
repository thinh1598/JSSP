"""KET HOP CP-SAT + Incremental SAT (thi nghiem cai tien, so voi cach A = chi dung SAT tu can heuristic).

Y tuong: CP-SAT gioi tim LICH TOT (can tren thap), SAT gioi CHUNG MINH can duoi. Cho CP-SAT chay NGAN truoc,
roi dua can cua no cho Incremental SAT (cnf o chan troi H nho hon, khoang tim kiem hep hon).

  A (co san)  : Incremental SAT tu [can don gian, lich heuristic]            (cac dong method = inc_binary)
  B           : CP-SAT chay ngan -> lay CAN TREN + lich; SAT bat dau tu can duoi don gian
  C           : CP-SAT chay ngan -> lay CAN TREN + lich va CAN DUOI; SAT bat dau tu hai can do

CONG BANG: tong thoi gian moi o (CP-SAT khoi dong + SAT) = ngan sach bang voi cach A / CP-SAT thuan.
Khoi dong CP-SAT chay MOT LAN moi bai va luu vao results/warmup/*.json (dung chung cho B va C, dung lai khi chay tiep);
thoi gian khoi dong van duoc tinh vao total_time cua ca hai bien the.
Ket qua cuoi la khoang HOP NHAT: cap duoi = max(cua SAT, cua CP-SAT), cap tren = min(...).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from .baselines import run_cpsat
from .heuristic import best_greedy
from .instance import read_instance
from .runner import CsvLog
from .search_multi import ROOT, SearchResult, search
from .validate import makespan

VARIANTS = ("B", "C")
DEFAULT_BUDGET = {"la21": 900, "orb01": 900}            # cac bai con lai: 3600 (khop voi lan chay co so sanh)
DEFAULT_INSTANCES = ["la21", "orb01", "abz7", "abz8", "abz9", "yn1"]


def hybrid_method(variant: str) -> str:
    return f"hybrid_{variant}"


def hybrid_solver_label(solver: str, tiny: bool, workers: int) -> str:
    return f"{'DPLL-tiny' if tiny else solver}+cpsat-w{workers}"


def get_warmup(path, warmup: float, workers: int, mem_limit_mb: Optional[float], out_dir,
               run_cp=run_cpsat, verbose: bool = True) -> Dict:
    """Chay (hoac doc lai tu dem) CP-SAT khoi dong. Tra ve dict: lb, ub, optimal, status, wall_time, peak_mem_mb, starts."""
    inst = read_instance(path)
    f = Path(out_dir).parent / "warmup" / f"{inst.name}_cpsat-w{workers}_{int(warmup)}s.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        d["cached"] = True
        if verbose:
            print(f"[hybrid] dung lai khoi dong CP-SAT da luu: {f.name}")
        return d
    r = run_cp(path, warmup, workers, 0, mem_limit_mb, None, None, verbose)
    d = {"instance": inst.name, "warmup_s": warmup, "workers": workers, "lb": r.lb, "ub": r.ub,
         "optimal": bool(r.optimal), "status": r.status, "wall_time": round(r.total_time, 2),
         "peak_mem_mb": r.peak_mem_mb, "starts": r.best_starts}
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d), encoding="utf-8")
    d["cached"] = False
    return d


def run_hybrid(path, variant: str, budget: float, warmup_frac: float = 0.2, solver: str = "cadical153",
               workers: int = 1, mem_limit_mb: Optional[float] = None, tiny: bool = False, out_dir=None,
               calls_log: Optional[CsvLog] = None, summary_log: Optional[CsvLog] = None,
               run_cp=run_cpsat, run_sat=search, verbose: bool = True) -> SearchResult:
    if variant not in VARIANTS:
        raise ValueError(f"bien the phai la mot trong {VARIANTS}")
    path = Path(path)
    inst = read_instance(path)
    out = Path(out_dir) if out_dir else ROOT / "results" / "raw"
    save_dir = out.parent / "schedules"
    warmup = budget * warmup_frac
    method, label = hybrid_method(variant), hybrid_solver_label(solver, tiny, workers)
    lb0 = inst.trivial_lower_bound()
    ub0 = makespan(inst, best_greedy(inst))

    wu = get_warmup(path, warmup, workers, mem_limit_mb, out, run_cp, verbose)
    t_wu = float(wu["wall_time"])
    lb_cp, ub_cp = int(wu["lb"]), int(wu["ub"])
    sat: Optional[SearchResult] = None
    peaks = [wu["peak_mem_mb"]] if wu.get("peak_mem_mb") is not None else []

    if wu["optimal"] or lb_cp >= ub_cp:                    # CP-SAT da chung minh toi uu trong luc khoi dong
        lb, ub, starts, status, n_calls, t_sat = ub_cp, ub_cp, wu["starts"], "OPTIMAL", 0, 0.0
    else:
        remain = budget - t_wu
        if remain < 1:                                      # khoi dong da an het ngan sach
            lb, ub, starts, status, n_calls, t_sat = lb_cp, ub_cp, wu["starts"], "TIMEOUT", 0, 0.0
        else:
            sat = run_sat(path, "inc_binary", solver, lb_cp if variant == "C" else None, None, remain, remain,
                          mem_limit_mb, tiny, calls_log, None, save_dir, verbose,
                          init_starts=wu["starts"], tag=method)
            lb, ub = max(sat.lb, lb_cp), min(sat.ub, ub_cp)
            starts = sat.best_starts if sat.ub <= ub_cp else wu["starts"]
            status = "OPTIMAL" if lb >= ub else sat.status
            n_calls, t_sat = sat.n_calls, sat.total_time
            if sat.peak_mem_mb is not None:
                peaks.append(sat.peak_mem_mb)
    optimal = lb >= ub
    total = t_wu + t_sat
    res = SearchResult(inst.name, method, label, lb, ub, optimal, "OPTIMAL" if optimal else status, n_calls,
                       total, starts, sat.calls if sat else [], max(peaks) if peaks else None)
    if verbose:
        print(f"[{method}] {inst.name}: {res.status}  LB={lb} UB={ub}  (CP-SAT {t_wu:.0f}s: [{lb_cp}, {ub_cp}] "
              f"+ SAT {t_sat:.0f}s)  tong {total:.0f}s")
    if summary_log:
        lb_src = (f"hop nhat: SAT tu CP-SAT {lb_cp}" if variant == "C"
                  else f"hop nhat: max(SAT tu {lb0}, CP-SAT {lb_cp})")
        summary_log.append({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "instance": inst.name,
                            "n_jobs": inst.n_jobs, "n_machines": inst.n_machines, "method": method, "solver": label,
                            "lb_init": lb0, "lb_source": lb_src, "ub_init": ub0,
                            "ub_source": f"heuristic {ub0} -> CP-SAT {warmup:.0f}s: {ub_cp}", "lb_final": lb,
                            "ub_final": ub, "optimal": res.optimal, "status": res.status, "n_calls": n_calls,
                            "total_time": round(total, 2),
                            "max_peak_mem_mb": "" if res.peak_mem_mb is None else res.peak_mem_mb})
    if sat is None and starts:                              # khong co pha SAT: luu lich cua CP-SAT
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / f"{inst.name}_{method}_{label}.json").write_text(
            json.dumps({"instance": inst.name, "makespan": ub, "optimal": res.optimal, "lb": lb, "starts": starts}),
            encoding="utf-8")
    return res
