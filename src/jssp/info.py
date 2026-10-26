"""In thong tin co ban cua mot bai JSSP.

Chay:  python -m jssp.info data/ft06.txt        (tu thu muc src/)  hoac
       python src/jssp/info.py data/ft06.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):          # chay truc tiep nhu script
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from jssp.instance import read_instance  # type: ignore
else:
    from .instance import read_instance


def describe(path: str) -> str:
    inst = read_instance(path)
    loads = inst.machine_loads()
    return (f"{inst.name}: {inst.n_jobs} job x {inst.n_machines} may\n"
            f"  tong so thao tac       : {sum(len(j) for j in inst.jobs)}\n"
            f"  job dai nhat           : {max(inst.job_length(l) for l in range(inst.n_jobs))}\n"
            f"  may tai nang nhat      : {max(loads)}\n"
            f"  LB don gian (max 2 so) : {inst.trivial_lower_bound()}\n"
            f"  UB don gian (noi tiep) : {inst.trivial_upper_bound()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Cach dung: python -m jssp.info <file bai>")
    for p in sys.argv[1:]:
        print(describe(p))
