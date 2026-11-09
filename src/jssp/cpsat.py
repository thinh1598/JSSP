"""Baseline CP-SAT (Google OR-Tools): mo hinh JSSP kinh dien bang khoang thoi gian (interval) va NoOverlap.

Khac voi ma hoa SAT (Crawford): o day KHONG co bien theo tung thoi diem t, solver lam viec truc tiep voi
"thoi diem bat dau" nguyen va cac rang buoc (thu tu trong job, khong chong nhau tren may).

De so sanh cong bang voi huong SAT, CP-SAT nhan CUNG thong tin ban dau:
  - can duoi lb (don gian: max do dai job, max tai may) -> makespan >= lb
  - can tren ub (makespan cua lich heuristic)           -> makespan <= ub, moi thoi diem bat dau <= ub - tail - p
va mac dinh chi dung 1 luong (workers=1) nhu CaDiCaL chay don luong. Chay nhieu luong la mot thi nghiem rieng.
"""
from __future__ import annotations

import time
from typing import Dict, Optional

from .instance import JSSPInstance


def build_model(inst: JSSPInstance, lb: int, ub: int):
    """Tra ve (model, start_vars, makespan_var). start_vars[l][i] la bien thoi diem bat dau cua thao tac (l, i)."""
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    start = []
    intervals_by_machine: Dict[int, list] = {}
    for l, job in enumerate(inst.jobs):
        total = sum(d for _, d in job)
        run = 0
        row = []
        for i, (m, d) in enumerate(job):
            head, tail = run, total - run - d
            # thao tac khong the bat dau truoc "head" (cac thao tac truoc trong job) va phai ket thuc truoc ub - tail
            s = model.NewIntVar(head, max(head, ub - tail - d), f"s_{l}_{i}")
            iv = model.NewFixedSizeIntervalVar(s, d, f"iv_{l}_{i}")
            intervals_by_machine.setdefault(m, []).append(iv)
            row.append(s)
            run += d
        start.append(row)

    for l, job in enumerate(inst.jobs):                      # thu tu trong job
        for i in range(len(job) - 1):
            model.Add(start[l][i + 1] >= start[l][i] + job[i][1])

    for ivs in intervals_by_machine.values():                # moi may mot viec mot luc
        model.AddNoOverlap(ivs)

    makespan = model.NewIntVar(lb, ub, "makespan")
    for l, job in enumerate(inst.jobs):
        model.Add(makespan >= start[l][-1] + job[-1][1])
    model.Minimize(makespan)
    return model, start, makespan


def solve_cpsat(inst: JSSPInstance, lb: int, ub: int, time_limit: float = 600.0, workers: int = 1,
                seed: int = 0) -> Dict:
    """Giai toi uu hoa makespan. Tra ve dict: status, makespan, best_bound, starts, wall_time, workers, version.

    status: OPTIMAL | FEASIBLE (het gio, co loi giai) | UNKNOWN (het gio, chua co loi giai) | INFEASIBLE | MODEL_INVALID
    """
    import ortools
    from ortools.sat.python import cp_model

    t0 = time.perf_counter()
    model, start, _ = build_model(inst, lb, ub)
    solver = cp_model.CpSolver()
    p = solver.parameters
    p.max_time_in_seconds = float(time_limit)
    p.random_seed = int(seed)
    try:
        p.num_workers = int(workers)               # ten moi (OR-Tools >= 9.10)
    except AttributeError:
        p.num_search_workers = int(workers)        # ten cu
    status = solver.Solve(model)
    name = solver.StatusName(status)

    starts = None
    makespan: Optional[int] = None
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        starts = [[int(solver.Value(v)) for v in row] for row in start]
        makespan = int(round(solver.ObjectiveValue()))
    return {"status": name, "makespan": makespan, "best_bound": float(solver.BestObjectiveBound()),
            "starts": starts, "wall_time": round(time.perf_counter() - t0, 3), "workers": int(workers),
            "version": getattr(ortools, "__version__", "?")}
