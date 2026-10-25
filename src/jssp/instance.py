"""Doc va mo ta mot bai toan Job-Shop Scheduling (JSSP).

Quy uoc:
  - jobs[l] la danh sach cac thao tac cua job l theo dung thu tu thuc hien.
  - Moi thao tac la cap (machine, duration); machine danh so tu 0, duration >= 1 (so nguyen).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

Operation = Tuple[int, int]  # (machine, duration)


@dataclass(frozen=True)
class JSSPInstance:
    name: str
    n_jobs: int
    n_machines: int
    jobs: List[List[Operation]]

    def job_length(self, l: int) -> int:
        """Tong thoi gian cua job l (can duoi cua makespan)."""
        return sum(d for _, d in self.jobs[l])

    def machine_loads(self) -> List[int]:
        """Tong thoi gian cac thao tac phai chay tren tung may."""
        loads = [0] * self.n_machines
        for job in self.jobs:
            for m, d in job:
                loads[m] += d
        return loads

    def trivial_lower_bound(self) -> int:
        """LB don gian: max(job dai nhat, may tai nang nhat)."""
        return max(max(self.job_length(l) for l in range(self.n_jobs)),
                   max(self.machine_loads()))

    def trivial_upper_bound(self) -> int:
        """UB don gian: chay noi tiep moi thao tac (luon kha thi)."""
        return sum(d for job in self.jobs for _, d in job)


def _build(name: str, ints: List[int]) -> JSSPInstance:
    if len(ints) < 2:
        raise ValueError(f"[{name}] thieu dong kich thuoc 'n m'")
    n, m = ints[0], ints[1]
    data = ints[2:]
    if n <= 0 or m <= 0:
        raise ValueError(f"[{name}] n, m phai duong (n={n}, m={m})")
    if len(data) != n * m * 2:
        raise ValueError(
            f"[{name}] can {n * m * 2} so cho {n} job x {m} thao tac, nhung co {len(data)}")
    jobs: List[List[Operation]] = []
    for l in range(n):
        row = data[l * m * 2:(l + 1) * m * 2]
        ops = [(row[2 * i], row[2 * i + 1]) for i in range(m)]
        for mach, dur in ops:
            if not 0 <= mach < m:
                raise ValueError(f"[{name}] job {l}: machine {mach} ngoai khoang 0..{m - 1}")
            if dur < 1:
                raise ValueError(f"[{name}] job {l}: duration {dur} < 1 (ma hoa Crawford can p >= 1)")
        jobs.append(ops)
    return JSSPInstance(name=name, n_jobs=n, n_machines=m, jobs=jobs)


def read_instance(path: str | Path) -> JSSPInstance:
    """Doc file mot bai (bo qua dong bat dau bang '#'). Ten bai = ten file khong duoi."""
    path = Path(path)
    ints: List[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        ints.extend(int(tok) for tok in line.split())
    return _build(path.stem, ints)


def read_orlib(path: str | Path) -> Dict[str, JSSPInstance]:
    """Doc file nhieu bai kieu OR-Library (jobshop1.txt): moi bai bat dau bang dong 'instance <ten>'.

    Chi nhan cac dong gom toan so nguyen sau dong tieu de; dong mo ta va dong '+++' bi bo qua.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    starts = [i for i, ln in enumerate(lines) if re.match(r"^\s*instance\s+\S+", ln, re.I)]
    result: Dict[str, JSSPInstance] = {}
    for k, s in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        name = lines[s].split()[1]
        ints: List[int] = []
        for ln in lines[s + 1:end]:
            toks = ln.split()
            if toks and all(re.fullmatch(r"-?\d+", t) for t in toks):
                ints.extend(int(t) for t in toks)
        result[name] = _build(name, ints)
    return result
