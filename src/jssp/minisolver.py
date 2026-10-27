"""Solver DPLL rat nho (2-watched-literals, quay lui) - CHI DE KIEM THU tren bai tI hon.

Khong dung cho thuc nghiem that: hay dung PySAT (CaDiCaL, Glucose, ...).
Muc dich: de doi chieu ma hoa Crawford ngay ca khi may chua cai PySAT.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional


def solve_dpll(clauses: List[List[int]], nvars: int) -> Optional[List[int]]:
    """Tra ve model (danh sach literal, moi bien xuat hien 1 lan) hoac None neu UNSAT."""
    if any(len(c) == 0 for c in clauses):
        return None

    val = [0] * (nvars + 1)               # 0 chua gan, 1 dung, -1 sai
    trail: List[int] = []
    watches: Dict[int, List[int]] = defaultdict(list)
    cl: List[List[int]] = []
    units: List[int] = []

    for c in clauses:
        c = list(dict.fromkeys(c))        # bo literal lap
        if any(-x in c for x in c):       # clause luon dung
            continue
        if len(c) == 1:
            units.append(c[0])
        else:
            watches[c[0]].append(len(cl))
            watches[c[1]].append(len(cl))
            cl.append(c)

    def value(lit: int) -> int:
        v = val[abs(lit)]
        return v if lit > 0 else -v

    def enqueue(lit: int, queue: List[int]) -> bool:
        v = value(lit)
        if v == 1:
            return True
        if v == -1:
            return False
        val[abs(lit)] = 1 if lit > 0 else -1
        trail.append(lit)
        queue.append(lit)
        return True

    def propagate(queue: List[int]) -> bool:
        while queue:
            fl = -queue.pop()             # literal vua bi lam sai
            ws = watches[fl]
            watches[fl] = []
            idx = 0
            while idx < len(ws):
                ci = ws[idx]
                idx += 1
                c = cl[ci]
                if c[0] == fl:
                    c[0], c[1] = c[1], c[0]
                if value(c[0]) == 1:
                    watches[fl].append(ci)
                    continue
                moved = False
                for k in range(2, len(c)):
                    if value(c[k]) != -1:
                        c[1], c[k] = c[k], c[1]
                        watches[c[1]].append(ci)
                        moved = True
                        break
                if moved:
                    continue
                watches[fl].append(ci)
                if value(c[0]) == -1:
                    watches[fl].extend(ws[idx:])
                    return False
                enqueue(c[0], queue)
        return True

    def undo(to_len: int) -> None:
        while len(trail) > to_len:
            val[abs(trail.pop())] = 0

    queue: List[int] = []
    for u in units:
        if not enqueue(u, queue):
            return None
    if not propagate(queue):
        return None

    stack: List[list] = []                # [do_dai_trail, literal_quyet_dinh, da_dao]
    while True:
        v = next((x for x in range(1, nvars + 1) if val[x] == 0), 0)
        if v == 0:
            return [x if val[x] == 1 else -x for x in range(1, nvars + 1)]
        stack.append([len(trail), -v, False])
        q: List[int] = []
        ok = enqueue(-v, q) and propagate(q)
        while not ok:
            while stack:
                tl, lit, flipped = stack.pop()
                undo(tl)
                if not flipped:
                    stack.append([tl, -lit, True])
                    q = []
                    ok = enqueue(-lit, q) and propagate(q)
                    break
            else:
                return None
