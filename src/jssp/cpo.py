"""Baseline CPLEX CP Optimizer (qua thu vien docplex.cp, chay chuong trinh cpoptimizer.exe cua Studio).

Mo hinh kinh dien: moi thao tac la mot interval_var co do dai co dinh; end_before_start trong job; no_overlap tren may;
makespan trong [lb, ub]. CUNG thong tin ban dau (lb, ub) va cung 1 luong (Workers=1) nhu CP-SAT / Gurobi / CaDiCaL.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .instance import JSSPInstance
from .studio import find_exe


def build_cpo_model(inst: JSSPInstance, lb: int, ub: int):
    """Tra ve (model, interval_vars[l][i], makespan_var)."""
    from docplex.cp.model import CpoModel

    mdl = CpoModel()
    iv: List[List] = []
    on_machine: Dict[int, list] = {}
    for l, job in enumerate(inst.jobs):
        total = sum(d for _, d in job)
        run = 0
        row = []
        for i, (m, d) in enumerate(job):
            head, tail = run, total - run - d
            v = mdl.interval_var(start=(head, max(head, ub - tail - d)), size=d, name=f"iv_{l}_{i}")
            on_machine.setdefault(m, []).append(v)
            row.append(v)
            run += d
        iv.append(row)
    for row in iv:
        for a, b in zip(row, row[1:]):
            mdl.add(mdl.end_before_start(a, b))
    for ivs in on_machine.values():
        if len(ivs) > 1:
            mdl.add(mdl.no_overlap(ivs))
    mk = mdl.integer_var(lb, ub, "makespan")
    for row in iv:
        mdl.add(mdl.end_of(row[-1]) <= mk)
    mdl.add(mdl.minimize(mk))
    return mdl, iv, mk


def map_cpo_status(solve_status: str, has_solution: bool) -> str:
    s = (solve_status or "").lower()
    if s == "optimal":
        return "OPTIMAL"
    if s == "infeasible":
        return "INFEASIBLE"
    return "FEASIBLE" if has_solution else "UNKNOWN"


def solve_cpo(inst: JSSPInstance, lb: int, ub: int, time_limit: float = 600.0, workers: int = 1,
              seed: int = 0) -> Dict:
    """Tra ve dict: status, makespan, best_bound, starts, wall_time, workers, version."""
    import docplex

    t0 = time.perf_counter()
    mdl, iv, _ = build_cpo_model(inst, lb, ub)
    kw = {"TimeLimit": float(time_limit), "Workers": int(workers), "RandomSeed": int(seed),
          "LogVerbosity": "Quiet"}
    exe = find_exe("cpoptimizer")
    if exe:
        kw["execfile"] = exe
    res = mdl.solve(**kw)
    has = bool(res.is_solution())
    status = map_cpo_status(str(res.get_solve_status()), has)
    starts: Optional[List[List[int]]] = None
    makespan: Optional[int] = None
    if has:
        starts = [[int(res.get_var_solution(v).get_start()) for v in row] for row in iv]
        makespan = int(round(res.get_objective_values()[0]))
    bound: Optional[float] = None
    try:
        b = res.get_objective_bounds()
        if b and b[0] is not None:
            bound = float(b[0])
    except Exception:                                        # noqa: BLE001
        bound = None
    return {"status": status, "makespan": makespan, "best_bound": bound, "starts": starts,
            "wall_time": round(time.perf_counter() - t0, 3), "workers": int(workers),
            "version": getattr(docplex, "__version__", "?")}
