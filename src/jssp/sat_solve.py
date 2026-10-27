"""Giai S_L bang SAT solver (PySAT) va giai ma + kiem tra lich."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from .crawford import CrawfordEncoder
from .instance import JSSPInstance
from .validate import makespan, validate_schedule

# backend(clauses, num_vars) -> model (danh sach literal co dau) neu SAT, None neu UNSAT
Backend = Callable[[Sequence[Sequence[int]], int], Optional[List[int]]]


def pysat_backend(solver_name: str = "cadical153") -> Backend:
    def run(clauses, num_vars):
        from pysat.solvers import Solver  # import tre de module van import duoc khi chua cai PySAT
        with Solver(name=solver_name, bootstrap_with=clauses) as s:
            if s.solve():
                return s.get_model()
        return None
    return run


@dataclass
class SolveResult:
    status: str                              # "SAT" hoac "UNSAT"
    L: int
    starts: Optional[List[List[int]]]
    makespan: Optional[int]
    num_vars: int
    num_clauses: int
    encode_time: float
    solve_time: float


def solve_le(inst: JSSPInstance, L: int, solver: str = "cadical153",
             backend: Optional[Backend] = None, check: bool = True) -> SolveResult:
    """Hoi: co lich hop le voi makespan <= L khong?  (giai S_L)"""
    t0 = time.perf_counter()
    enc = CrawfordEncoder(inst, L)
    t1 = time.perf_counter()
    if enc.trivially_unsat:
        return SolveResult("UNSAT", L, None, None, 0, 0, t1 - t0, 0.0)

    run = backend or pysat_backend(solver)
    model = run(enc.clauses, enc.num_vars)
    t2 = time.perf_counter()
    if model is None:
        return SolveResult("UNSAT", L, None, None, enc.num_vars, len(enc.clauses), t1 - t0, t2 - t1)

    starts = enc.decode(model)
    if check:
        errs = validate_schedule(inst, starts, L)
        if errs:
            raise RuntimeError("Nghiem SAT giai ma ra lich KHONG hop le (loi ma hoa/giai ma):\n  "
                               + "\n  ".join(errs[:10]))
    return SolveResult("SAT", L, starts, makespan(inst, starts), enc.num_vars, len(enc.clauses),
                       t1 - t0, t2 - t1)
