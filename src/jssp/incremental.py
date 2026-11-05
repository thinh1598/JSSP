"""INCREMENTAL SAT: ma hoa MOT LAN o chan troi H, doi L bang "gia dinh" (assumptions).

So voi "SAT nhieu lan" (search_multi: moi L la mot CNF moi, solver moi):
  - cong thuc goc chi sinh 1 lan voi H = can tren ban dau (hi);
  - L nho hon duoc ep bang cac literal gia dinh  eb[a, L - tail(a)]  (xem CrawfordEncoder.assumptions_for);
  - solver giu lai cac clause da hoc duoc giua cac lan hoi, vi cong thuc goc khong doi.

Cai gia phai tra: cong thuc o chan troi H lon hon cong thuc o L nho (nhieu bien/clause hon).

Hai cach chon L giong search_multi: 'descent' (L = hi-1) va 'binary' (L = (lo+hi)//2).
"""
from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Sequence

from .crawford import CrawfordEncoder
from .instance import JSSPInstance
from .validate import makespan, validate_schedule

# factory(clauses, num_vars) -> doi tuong co .solve(assumptions) -> model | None  va  .close()
SolverFactory = Callable[[Sequence[Sequence[int]], int], "object"]


class PySatIncremental:
    """Solver PySAT giu nguyen giua cac lan solve (incremental that su)."""

    def __init__(self, clauses, num_vars, solver_name: str = "cadical153"):
        from pysat.solvers import Solver  # import tre de module van import duoc khi chua cai PySAT
        self._s = Solver(name=solver_name, bootstrap_with=clauses)

    def solve(self, assumptions: Sequence[int]) -> Optional[List[int]]:
        if self._s.solve(assumptions=list(assumptions)):
            return self._s.get_model()
        return None

    def close(self) -> None:
        self._s.delete()


class RestartingAdapter:
    """KHONG phai incremental that: moi lan hoi giai lai tu dau voi gia dinh them thanh clause don.
    Chi de kiem thu logic (vd. voi DPLL nho --tiny) khi khong co PySAT."""

    def __init__(self, clauses, num_vars, fn):
        self._clauses = [list(c) for c in clauses]
        self._n = num_vars
        self._fn = fn

    def solve(self, assumptions: Sequence[int]) -> Optional[List[int]]:
        return self._fn(self._clauses + [[a] for a in assumptions], self._n)

    def close(self) -> None:
        pass


def pysat_factory(solver_name: str = "cadical153") -> SolverFactory:
    return lambda clauses, n: PySatIncremental(clauses, n, solver_name)


def restarting_factory(fn) -> SolverFactory:
    return lambda clauses, n: RestartingAdapter(clauses, n, fn)


class IncrementalSession:
    """Ma hoa o chan troi H roi tra loi nhieu cau hoi 'co lich makespan <= L khong?' (L <= H)."""

    def __init__(self, inst: JSSPInstance, H: int, factory: SolverFactory):
        t0 = time.perf_counter()
        self.inst = inst
        self.H = H
        self.enc = CrawfordEncoder(inst, H)
        if self.enc.trivially_unsat:
            raise ValueError(f"chan troi H={H} nho hon do dai mot job: khong co lich nao")
        self.solver = factory(self.enc.clauses, self.enc.num_vars)
        self.encode_time = time.perf_counter() - t0
        self.num_queries = 0

    @property
    def num_vars(self) -> int:
        return self.enc.num_vars

    @property
    def num_clauses(self) -> int:
        return len(self.enc.clauses)

    def query(self, L: int) -> Dict:
        """Hoi S_L. Tra ve dict: L, status (SAT/UNSAT), starts, makespan, solve_time."""
        self.num_queries += 1
        t0 = time.perf_counter()
        assum = self.enc.assumptions_for(L)          # nem ValueError neu L > H
        model = None if assum is None else self.solver.solve(assum)
        dt = time.perf_counter() - t0
        if model is None:
            return {"L": L, "status": "UNSAT", "starts": None, "makespan": None, "valid": None,
                    "solve_time": round(dt, 3), "wall_time": round(dt, 3)}
        starts = self.enc.decode(model)
        errs = validate_schedule(self.inst, starts, L)
        if errs:
            raise RuntimeError("Nghiem SAT (incremental) giai ma ra lich KHONG hop le:\n  " + "\n  ".join(errs[:10]))
        return {"L": L, "status": "SAT", "starts": starts, "makespan": makespan(self.inst, starts),
                "valid": True, "solve_time": round(dt, 3), "wall_time": round(dt, 3)}

    def close(self) -> None:
        self.solver.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def incremental_search(session: IncrementalSession, method: str, lo: int, hi: int,
                       emit: Optional[Callable[[Dict], None]] = None):
    """Vong tim toi uu tren mot phien incremental. Can session.H >= hi.

    lo = can duoi da chung minh, hi = makespan cua lich da co. Tra ve (lo, hi); xong khi lo == hi."""
    if method not in ("descent", "binary"):
        raise ValueError("method phai la 'descent' hoac 'binary'")
    if session.H < hi:
        raise ValueError(f"chan troi H={session.H} nho hon hi={hi}")
    while lo < hi:
        L = hi - 1 if method == "descent" else (lo + hi) // 2
        r = session.query(L)
        if emit:
            emit(r)
        if r["status"] == "SAT":
            hi = r["makespan"]                        # <= L < hi nen vong luon tien len
        else:
            lo = hi if method == "descent" else L + 1
    return lo, hi
