"""Ma hoa Crawford (Crawford & Baker 1994) cho JSSP, theo Koshimura et al. 2010, muc 2.

S_L thoa duoc  <=>  ton tai lich hop le co makespan <= L.

Quy uoc chi so: job l = 0..n-1, thao tac i = 0..q_l-1, thoi gian t = 0..L (khac bai bao danh so tu 1).
Mot thao tac duoc ky hieu bang tuple op = (l, i).

Bien (danh so tu 1, dung DIMACS):
  pr[a,b]  : thao tac a dung TRUOC thao tac b           (chi tao cho cap cung job lien tiep, cung may)
  sa[a,t]  : a bat dau tu thoi diem t tro di (start >= t),      t = 0..L
  eb[a,t]  : a ket thuc truoc hoac tai t   (end   <= t),         t = 0..L

Cac quy tac (R1..R8 la cua bai bao; R9 la bo sung cua nhom, xem notes/crawford_notes.md):
  R1  pr[(l,i),(l,i+1)]                                   thu tu trong job
  R2  pr[a,b] v pr[b,a]       (a, b cung may, khac job)   hai thao tac cung may khong chong nhau
  R3  sa[a, head(a)]                                      head = tong p cac thao tac truoc trong job
  R4  eb[a, L - tail(a)]                                  tail = tong p cac thao tac sau trong job
  R5  sa[a,t] -> sa[a,t-1]                1 <= t <= L
  R6  eb[a,t] -> eb[a,t+1]                0 <= t <  L
  R7  sa[a,t] -> not eb[a, t+p-1]         0 <= t <= L-p
  R8  sa[a,t] ^ pr[a,b] -> sa[b, t+p]     0 <= t <= L-p      (voi moi bien pr[a,b], p = p_a)
  R9  not sa[a,t]                         L-p+1 <= t <= L   (bo sung: thao tac khong the bat dau qua muon)
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from .instance import JSSPInstance

Op = Tuple[int, int]  # (job, thu tu thao tac), deu tu 0


class CrawfordEncoder:
    def __init__(self, inst: JSSPInstance, L: int, boundary_units: bool = True):
        """boundary_units=True them R9 (mac dinh). Dat False de chay dung nguyen 8 quy tac bai bao."""
        self.inst = inst
        self.L = L
        self.boundary_units = boundary_units
        self.clauses: List[List[int]] = []
        self.rule_ranges: Dict[str, Tuple[int, int]] = {}  # ten quy tac -> [dau, cuoi) trong clauses
        self.num_vars = 0
        self.trivially_unsat = False

        self._ops: List[Op] = [(l, i) for l in range(inst.n_jobs) for i in range(len(inst.jobs[l]))]
        self._idx: Dict[Op, int] = {op: k for k, op in enumerate(self._ops)}
        self._m: Dict[Op, int] = {(l, i): inst.jobs[l][i][0] for (l, i) in self._ops}
        self._p: Dict[Op, int] = {(l, i): inst.jobs[l][i][1] for (l, i) in self._ops}
        self._head: Dict[Op, int] = {}
        self._tail: Dict[Op, int] = {}
        for l, job in enumerate(inst.jobs):
            total = sum(d for _, d in job)
            run = 0
            for i, (_, d) in enumerate(job):
                self._head[(l, i)] = run
                self._tail[(l, i)] = total - run - d
                run += d
        self._pr: Dict[Tuple[Op, Op], int] = {}

        # Neu mot job da dai hon L thi chac chan khong co lich: khong can sinh CNF.
        if L < 0 or any(self._head[o] + self._p[o] + self._tail[o] > L for o in self._ops):
            self.trivially_unsat = True
            return
        self._build()

    # ------------------------------------------------------------------ bien
    def pr(self, a: Op, b: Op) -> int:
        return self._pr[(a, b)]

    def sa(self, op: Op, t: int) -> int:
        return self._sa_base + self._idx[op] * (self.L + 1) + t

    def eb(self, op: Op, t: int) -> int:
        return self._eb_base + self._idx[op] * (self.L + 1) + t

    # ------------------------------------------------------------------ sinh clause
    def _build(self) -> None:
        L = self.L
        ops = self._ops
        p, head, tail, idx = self._p, self._head, self._tail, self._idx
        cl = self.clauses

        # --- cap thao tac can bien pr
        job_pairs: List[Tuple[Op, Op]] = [((l, i), (l, i + 1))
                                          for l, job in enumerate(self.inst.jobs) for i in range(len(job) - 1)]
        by_machine: Dict[int, List[Op]] = {}
        for op in ops:
            by_machine.setdefault(self._m[op], []).append(op)
        mach_pairs: List[Tuple[Op, Op]] = []
        for _, lst in sorted(by_machine.items()):
            for x in range(len(lst)):
                for y in range(x + 1, len(lst)):
                    a, b = lst[x], lst[y]
                    if a[0] != b[0]:          # ops sap theo job nen a.job < b.job (1 <= l < k <= n)
                        mach_pairs.append((a, b))

        nxt = 1
        for a, b in job_pairs:
            self._pr[(a, b)] = nxt
            nxt += 1
        for a, b in mach_pairs:
            self._pr[(a, b)] = nxt
            self._pr[(b, a)] = nxt + 1
            nxt += 2
        n_pr = nxt - 1
        self._sa_base = n_pr + 1
        self._eb_base = self._sa_base + len(ops) * (L + 1)
        self.num_vars = n_pr + 2 * len(ops) * (L + 1)

        def mark(name: str, begin: int) -> None:
            self.rule_ranges[name] = (begin, len(cl))

        # R1
        b0 = len(cl)
        for a, b in job_pairs:
            cl.append([self._pr[(a, b)]])
        mark("R1", b0)
        # R2
        b0 = len(cl)
        for a, b in mach_pairs:
            cl.append([self._pr[(a, b)], self._pr[(b, a)]])
        mark("R2", b0)
        # R3
        b0 = len(cl)
        for op in ops:
            cl.append([self.sa(op, head[op])])
        mark("R3", b0)
        # R4
        b0 = len(cl)
        for op in ops:
            cl.append([self.eb(op, L - tail[op])])
        mark("R4", b0)
        # R5
        b0 = len(cl)
        for op in ops:
            base = self._sa_base + idx[op] * (L + 1)
            for t in range(1, L + 1):
                cl.append([-(base + t), base + t - 1])
        mark("R5", b0)
        # R6
        b0 = len(cl)
        for op in ops:
            base = self._eb_base + idx[op] * (L + 1)
            for t in range(0, L):
                cl.append([-(base + t), base + t + 1])
        mark("R6", b0)
        # R7
        b0 = len(cl)
        for op in ops:
            sb = self._sa_base + idx[op] * (L + 1)
            eb = self._eb_base + idx[op] * (L + 1)
            d = p[op]
            for t in range(0, L - d + 1):
                cl.append([-(sb + t), -(eb + t + d - 1)])
        mark("R7", b0)
        # R8
        b0 = len(cl)
        for (a, b), v in self._pr.items():
            d = p[a]
            sa_a = self._sa_base + idx[a] * (L + 1)
            sa_b = self._sa_base + idx[b] * (L + 1)
            for t in range(0, L - d + 1):
                cl.append([-(sa_a + t), -v, sa_b + t + d])
        mark("R8", b0)
        # R9 (bo sung)
        b0 = len(cl)
        if self.boundary_units:
            for op in ops:
                sb = self._sa_base + idx[op] * (L + 1)
                for t in range(L - p[op] + 1, L + 1):
                    cl.append([-(sb + t)])
        mark("R9", b0)

    # ------------------------------------------------------------------ giai ma
    def decode(self, model: Sequence[int]) -> List[List[int]]:
        """Tu phep gan (danh sach literal co dau cua solver) suy ra thoi diem bat dau.

        start(a) = t lon nhat sao cho sa[a,t] dung  (muc 2 cua bai bao).
        """
        truth = bytearray(self.num_vars + 1)
        for lit in model:
            if 0 < lit <= self.num_vars:
                truth[lit] = 1
        starts = [[0] * len(job) for job in self.inst.jobs]
        for op in self._ops:
            base = self._sa_base + self._idx[op] * (self.L + 1)
            t = self.L
            while t > 0 and not truth[base + t]:
                t -= 1
            starts[op[0]][op[1]] = t
        return starts

    # ------------------------------------------------------------------ de doc / hoc
    @staticmethod
    def op_name(op: Op) -> str:
        l, i = op
        return f"{chr(ord('A') + l) if l < 26 else 'J' + str(l)}{i + 1}"

    def name_of(self, v: int) -> str:
        """Ten de doc cua bien v, vi du 'sa[B2,t>=2]', 'eb[A1,end<=6]', 'pr[A1<B2]'."""
        v = abs(v)
        if v >= self._eb_base:
            k, t = divmod(v - self._eb_base, self.L + 1)
            return f"eb[{self.op_name(self._ops[k])},end<={t}]"
        if v >= self._sa_base:
            k, t = divmod(v - self._sa_base, self.L + 1)
            return f"sa[{self.op_name(self._ops[k])},t>={t}]"
        for (a, b), vid in self._pr.items():
            if vid == v:
                return f"pr[{self.op_name(a)}<{self.op_name(b)}]"
        return f"x{v}"

    def format_clause(self, c: Sequence[int]) -> str:
        return " v ".join(("NOT " if lit < 0 else "") + self.name_of(lit) for lit in c)

    def stats(self) -> Dict[str, int]:
        s = {"vars": self.num_vars, "clauses": len(self.clauses)}
        for name, (a, b) in self.rule_ranges.items():
            s[name] = b - a
        return s
