"""Heuristic xep lich nhanh de lay CAN TREN (UB) ban dau cho vong tim toi uu.

Lich nay khong toi uu, nhung luon HOP LE (da kiem tra bang validate o noi goi) va co makespan >= toi uu,
nen la mot UB co that (co lich kem theo), khac voi UB lay tu tai lieu.
"""
from __future__ import annotations

import random
from typing import List

from .instance import JSSPInstance
from .validate import makespan


def dispatch(inst: JSSPInstance, rule: str = "mwkr", rng: random.Random | None = None) -> List[List[int]]:
    """Xep lich theo quy tac uu tien: moi buoc chon thao tac (trong cac thao tac ke tiep cua tung job)
    co the bat dau som nhat; hoa thi chon theo quy tac:
      mwkr = job con nhieu viec nhat, spt = thao tac ngan nhat, lpt = dai nhat, rand = ngau nhien.
    """
    n = inst.n_jobs
    nxt = [0] * n
    job_ready = [0] * n
    mach_ready: dict = {}
    remaining = [sum(d for _, d in job) for job in inst.jobs]
    starts = [[0] * len(job) for job in inst.jobs]
    left = sum(len(job) for job in inst.jobs)
    while left:
        best = None
        for l in range(n):
            i = nxt[l]
            if i >= len(inst.jobs[l]):
                continue
            m, d = inst.jobs[l][i]
            est = max(job_ready[l], mach_ready.get(m, 0))
            if rule == "mwkr":
                key = (est, -remaining[l], l)
            elif rule == "spt":
                key = (est, d, l)
            elif rule == "lpt":
                key = (est, -d, l)
            elif rule == "rand":
                key = (est, rng.random() if rng else 0.0, l)
            else:
                raise ValueError(f"quy tac khong biet: {rule}")
            if best is None or key < best[0]:
                best = (key, l, est, d, m)
        _, l, est, d, m = best
        starts[l][nxt[l]] = est
        job_ready[l] = est + d
        mach_ready[m] = est + d
        remaining[l] -= d
        nxt[l] += 1
        left -= 1
    return starts


def best_greedy(inst: JSSPInstance, random_tries: int = 30, seed: int = 0) -> List[List[int]]:
    """Thu vai quy tac + vai chuc lan ngau nhien, lay lich co makespan nho nhat."""
    rng = random.Random(seed)
    cands = [dispatch(inst, r) for r in ("mwkr", "spt", "lpt")]
    cands += [dispatch(inst, "rand", rng) for _ in range(random_tries)]
    return min(cands, key=lambda s: makespan(inst, s))
