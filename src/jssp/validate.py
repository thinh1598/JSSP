"""Kiem tra mot lich co hop le hay khong - DOC LAP voi ma hoa SAT.

Moi nghiem ma SAT solver tra ve deu phai qua ham nay (neu khong qua = loi ma hoa/giai ma).
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from .instance import JSSPInstance


def makespan(inst: JSSPInstance, starts: Sequence[Sequence[int]]) -> int:
    return max(starts[l][i] + inst.jobs[l][i][1]
               for l in range(inst.n_jobs) for i in range(len(inst.jobs[l])))


def validate_schedule(inst: JSSPInstance, starts: Sequence[Sequence[int]],
                      L: Optional[int] = None) -> List[str]:
    """Tra ve danh sach loi (rong = lich hop le). Kiem tra:
    - dung hinh dang, thoi diem bat dau la so nguyen >= 0
    - thu tu trong job: thao tac i+1 chi bat dau sau khi thao tac i ket thuc
    - moi may chi lam mot viec mot luc (cac khoang [start, end) khong chong nhau)
    - (neu co L) makespan <= L
    """
    errs: List[str] = []
    if len(starts) != inst.n_jobs:
        return [f"so job trong lich ({len(starts)}) != {inst.n_jobs}"]
    for l, job in enumerate(inst.jobs):
        if len(starts[l]) != len(job):
            errs.append(f"job {l}: co {len(starts[l])} thoi diem bat dau, can {len(job)}")
    if errs:
        return errs

    per_machine: dict = {}
    for l, job in enumerate(inst.jobs):
        for i, (m, d) in enumerate(job):
            s = starts[l][i]
            if not isinstance(s, int) or s < 0:
                errs.append(f"job {l} thao tac {i}: thoi diem bat dau khong hop le ({s!r})")
                continue
            if i > 0:
                prev_end = starts[l][i - 1] + job[i - 1][1]
                if s < prev_end:
                    errs.append(f"job {l}: thao tac {i} bat dau {s} < thao tac {i - 1} ket thuc {prev_end}")
            per_machine.setdefault(m, []).append((s, s + d, l, i))

    for m, items in per_machine.items():
        items.sort()
        for (s1, e1, l1, i1), (s2, e2, l2, i2) in zip(items, items[1:]):
            if e1 > s2:
                errs.append(f"may {m}: (job {l1}, op {i1}) [{s1},{e1}) chong (job {l2}, op {i2}) [{s2},{e2})")

    if not errs and L is not None:
        ms = makespan(inst, starts)
        if ms > L:
            errs.append(f"makespan {ms} > L = {L}")
    return errs
