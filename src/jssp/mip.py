"""Mo hinh MIP (big-M, rang buoc tuyen) cho JSSP, viet DOC LAP voi solver.

Tai sao tach rieng?  De CPLEX MIP va Gurobi dung CHUNG mot cong thuc, va de kiem chung cong thuc bang phep vet can
tren bai nho MA KHONG CAN solver (tren may khong co Gurobi van test duoc).

Bien:
  s[a]   thoi diem bat dau cua thao tac a = (job, vi tri), nguyen, trong [head(a), ub - tail(a) - p(a)]
  C      makespan, nguyen, trong [lb, ub]
  y[a,b] nhi phan voi moi cap thao tac a, b KHAC JOB tren CUNG MAY (a xep truoc b trong danh sach):
           y = 1  <=>  a chay truoc b;   y = 0  <=>  b chay truoc a
Rang buoc (tat ca co dang  s[x] - s[w] >= c + he_so * y):
  thu tu trong job:  s[(l,i+1)] >= s[(l,i)] + p
  makespan:          C >= s[(l,cuoi)] + p
  khong chong nhau:  s[b] >= s[a] + p(a) - M1*(1 - y)      M1 = hi(a) + p(a) - lo(b)
                     s[a] >= s[b] + p(b) - M2*y            M2 = hi(b) + p(b) - lo(a)
  M1, M2 la hang so LON NHAT CAN THIET (suy ra tu can head/tail va ub), nen ham noi long chat hon big-M tho.
Muc tieu: cuc tieu C.

head(a) = tong p cac thao tac truoc a trong job; tail(a) = tong p cac thao tac sau a (giong crawford.py).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .instance import JSSPInstance

Op = Tuple[int, int]            # (job, vi tri)
CMAX = ("C",)                   # nut dai dien cho bien makespan


@dataclass(frozen=True)
class DiffCon:
    """s[x] - s[w] >= c + coef * y[ykey]   (ykey None: khong co so hang y)."""
    x: tuple
    w: tuple
    c: int
    ykey: Optional[Tuple[Op, Op]] = None
    coef: int = 0


@dataclass
class MipSpec:
    ops: List[Op]
    dur: Dict[Op, int]
    lo: Dict[tuple, int]              # can duoi cua s[a] va cua CMAX
    hi: Dict[tuple, int]              # can tren
    cons: List[DiffCon]
    ykeys: List[Tuple[Op, Op]]
    lb: int
    ub: int


def build_mip(inst: JSSPInstance, lb: int, ub: int) -> MipSpec:
    ops: List[Op] = []
    dur: Dict[Op, int] = {}
    lo: Dict[tuple, int] = {}
    hi: Dict[tuple, int] = {}
    on_machine: Dict[int, List[Op]] = {}
    for l, job in enumerate(inst.jobs):
        total = sum(d for _, d in job)
        run = 0
        for i, (m, d) in enumerate(job):
            a = (l, i)
            head, tail = run, total - run - d
            ops.append(a)
            dur[a] = d
            lo[a] = head
            hi[a] = max(head, ub - tail - d)
            on_machine.setdefault(m, []).append(a)
            run += d
    lo[CMAX], hi[CMAX] = lb, ub

    cons: List[DiffCon] = []
    for l, job in enumerate(inst.jobs):
        for i in range(len(job) - 1):
            cons.append(DiffCon((l, i + 1), (l, i), dur[(l, i)]))
        cons.append(DiffCon(CMAX, (l, len(job) - 1), dur[(l, len(job) - 1)]))

    ykeys: List[Tuple[Op, Op]] = []
    for m in sorted(on_machine):
        for a, b in itertools.combinations(on_machine[m], 2):
            if a[0] == b[0]:
                continue                                     # cung job: da co thu tu trong job
            key = (a, b)
            ykeys.append(key)
            m1 = hi[a] + dur[a] - lo[b]
            m2 = hi[b] + dur[b] - lo[a]
            cons.append(DiffCon(b, a, dur[a] - m1, key, m1))     # s_b - s_a >= p_a - M1 + M1*y
            cons.append(DiffCon(a, b, dur[b], key, -m2))         # s_a - s_b >= p_b - M2*y
    return MipSpec(ops, dur, lo, hi, cons, ykeys, lb, ub)


# ---------------------------------------------------------------- kiem chung doc lap voi solver
def check_assignment(spec: MipSpec, s: Dict[Op, int], y: Dict[Tuple[Op, Op], int], cmax: int) -> List[str]:
    """Mot loi giai (s, y, C) co thoa MOI rang buoc va can cua mo hinh khong? Tra ve danh sach vi pham."""
    val = dict(s)
    val[CMAX] = cmax
    errs = []
    for node, v in val.items():
        if not (spec.lo[node] <= v <= spec.hi[node]):
            errs.append(f"{node}={v} ngoai [{spec.lo[node]}, {spec.hi[node]}]")
    for k in spec.cons:
        rhs = k.c + (k.coef * y[k.ykey] if k.ykey is not None else 0)
        if val[k.x] - val[k.w] < rhs:
            errs.append(f"vi pham {k.x} - {k.w} >= {rhs}")
    return errs


def y_from_starts(spec: MipSpec, starts: Sequence[Sequence[int]]) -> Dict[Tuple[Op, Op], int]:
    """Suy ra y tu mot lich (y = 1 neu a bat dau truoc b)."""
    return {(a, b): int(starts[a[0]][a[1]] <= starts[b[0]][b[1]]) for a, b in spec.ykeys}


def earliest_for_fixed_y(spec: MipSpec, y: Dict[Tuple[Op, Op], int]) -> Optional[Dict[tuple, int]]:
    """Voi y co dinh moi rang buoc la rang buoc hieu  s[x] >= s[w] + c'. Nghiem 'som nhat' = duong dai nhat
    bat dau tu can duoi. Tra ve None neu vo nghiem (chu trinh duong, hoac vuot can tren)."""
    val = dict(spec.lo)
    cons = [(k.x, k.w, k.c + (k.coef * y[k.ykey] if k.ykey is not None else 0)) for k in spec.cons]
    for _ in range(len(val) + 1):
        changed = False
        for x, w, c in cons:
            if val[w] + c > val[x]:
                val[x] = val[w] + c
                changed = True
                if val[x] > spec.hi[x]:
                    return None
        if not changed:
            return val
    return None                                              # van con thay doi: chu trinh duong


def optimum_by_enumeration(spec: MipSpec) -> Optional[int]:
    """Gia tri toi uu cua mo hinh, bang cach thu MOI cach chon y (chi cho bai rat nho: 2^so_cap)."""
    best = None
    for bits in itertools.product((0, 1), repeat=len(spec.ykeys)):
        y = dict(zip(spec.ykeys, bits))
        val = earliest_for_fixed_y(spec, y)
        if val is not None and (best is None or val[CMAX] < best):
            best = val[CMAX]
    return best
