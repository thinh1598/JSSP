"""Baseline Gurobi (MIP): dung mo hinh big-M trong mip.py.

Cung quy cach cong bang nhu CP-SAT / SAT: cung can duoi lb, can tren ub (tu heuristic), mac dinh 1 luong
(threads=1), cung ngan sach gio. Khong truyen "MIP start": thong tin ban dau chi la hai can lb, ub, giong CP-SAT.
Chay nhieu luong (threads>1) la mot thi nghiem rieng.
"""
from __future__ import annotations

import time
from typing import Dict, Optional

from .instance import JSSPInstance
from .mip import CMAX, build_mip

# Ma trang thai cua Gurobi (GRB.Status): viet so thang de ham quy doi test duoc ma khong can cai Gurobi
G_OPTIMAL, G_INFEASIBLE, G_INF_OR_UNBD = 2, 3, 4


def map_status(code: int, sol_count: int) -> str:
    """Quy ve cung tu vung voi CP-SAT: OPTIMAL | FEASIBLE | UNKNOWN | INFEASIBLE."""
    if code == G_OPTIMAL:
        return "OPTIMAL"
    if code in (G_INFEASIBLE, G_INF_OR_UNBD):
        return "INFEASIBLE"
    return "FEASIBLE" if sol_count > 0 else "UNKNOWN"


def solve_gurobi(inst: JSSPInstance, lb: int, ub: int, time_limit: float = 600.0, threads: int = 1,
                 seed: int = 0) -> Dict:
    """Tra ve dict: status, makespan, best_bound, starts, wall_time, threads, version."""
    import gurobipy as gp
    from gurobipy import GRB

    t0 = time.perf_counter()
    spec = build_mip(inst, lb, ub)
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    m = gp.Model("jssp", env=env)
    s = {a: m.addVar(lb=spec.lo[a], ub=spec.hi[a], vtype=GRB.INTEGER, name=f"s_{a[0]}_{a[1]}") for a in spec.ops}
    c = m.addVar(lb=spec.lo[CMAX], ub=spec.hi[CMAX], vtype=GRB.INTEGER, name="C")
    y = {k: m.addVar(vtype=GRB.BINARY, name=f"y_{k[0][0]}_{k[0][1]}_{k[1][0]}_{k[1][1]}") for k in spec.ykeys}
    node = dict(s)
    node[CMAX] = c
    for k in spec.cons:
        expr = node[k.x] - node[k.w]
        if k.ykey is not None:
            expr = expr - k.coef * y[k.ykey]
        m.addConstr(expr >= k.c)
    m.setObjective(c, GRB.MINIMIZE)
    m.Params.TimeLimit = float(time_limit)
    m.Params.Threads = int(threads)
    m.Params.Seed = int(seed)
    m.Params.MIPGap = 0.0                       # ham muc tieu nguyen: chi dung khi chung minh toi uu that su
    m.optimize()

    status = map_status(m.Status, m.SolCount)
    starts = None
    makespan: Optional[int] = None
    if m.SolCount > 0:
        starts = [[int(round(s[(l, i)].X)) for i in range(len(job))] for l, job in enumerate(inst.jobs)]
        makespan = int(round(m.ObjVal))
    try:
        bound: Optional[float] = float(m.ObjBound)
    except (AttributeError, gp.GurobiError):
        bound = None
    return {"status": status, "makespan": makespan, "best_bound": bound, "starts": starts,
            "wall_time": round(time.perf_counter() - t0, 3), "threads": int(threads),
            "version": ".".join(str(v) for v in gp.gurobi.version())}
