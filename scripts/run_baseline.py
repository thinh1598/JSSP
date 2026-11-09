"""Chay BASELINE (hien co: CP-SAT cua OR-Tools) va ghi vao cung results/raw/summary.csv voi cac cach SAT.

Vi du (chay tu thu muc goc repo, da cai:  pip install ortools):
    python scripts/run_baseline.py ft06 la01
    python scripts/run_baseline.py ft10 la02 la03 la04 --time-limit 600
    python scripts/run_baseline.py ft10 --workers 8          # thi nghiem them: CP-SAT nhieu luong
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.baselines import run_cpsat  # noqa: E402
from jssp.runner import CsvLog  # noqa: E402
from jssp.search_multi import SUMMARY_FIELDS, resolve_instance  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instances", nargs="+", help="ten bai (ft06, la01, ...) hoac duong dan file")
    ap.add_argument("--model", choices=["cpsat"], default="cpsat")
    ap.add_argument("--time-limit", type=float, default=600, help="giay cho moi bai")
    ap.add_argument("--workers", type=int, default=1, help="mac dinh 1 = cong bang voi CaDiCaL don luong")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mem-limit-mb", type=float, default=None)
    ap.add_argument("--out", default=str(ROOT / "results" / "raw"))
    args = ap.parse_args()

    out = Path(args.out)
    summary_log = CsvLog(out / "summary.csv", SUMMARY_FIELDS)
    rows = []
    for name in args.instances:
        path = resolve_instance(name)
        print(f"\n=== {path.stem} | cpsat (workers={args.workers}, gioi han {args.time_limit:.0f}s) ===")
        rows.append(run_cpsat(path, args.time_limit, args.workers, args.seed, args.mem_limit_mb, summary_log,
                              ROOT / "results" / "schedules"))

    print("\n" + "=" * 70)
    print(f"{'bai':8s} {'ket qua':12s} {'LB':>6s} {'UB':>6s} {'giay':>9s}")
    for r in rows:
        verdict = f"toi uu {r.ub}" if r.optimal else r.status
        print(f"{r.instance:8s} {verdict:12s} {r.lb:6d} {r.ub:6d} {r.total_time:9.1f}")
    print(f"\nDa ghi: {out / 'summary.csv'}")
    return 0 if all(r.optimal for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
