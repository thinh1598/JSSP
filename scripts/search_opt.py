"""Tim makespan TOI UU bang SAT nhieu lan (giam dan / chia doi), ghi CSV.

Vi du (chay tu thu muc goc repo):
    python scripts/search_opt.py ft06 --method both
    python scripts/search_opt.py ft06 la01 la02 --method binary --per-call-timeout 300
    python scripts/search_opt.py ft10 --method binary --total-timeout 3600 --mem-limit-mb 8000
    python scripts/search_opt.py abz9 --ub 678 --lb 662 --method binary      # dung can tai lieu (UB duoc xac nhan 1 lan giai)

Ket qua: results/raw/calls.csv (moi lan giai mot dong), results/raw/summary.csv (moi lan tim mot dong),
         results/schedules/<bai>_<cach>_<solver>.json (lich tot nhat tim duoc).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.runner import CsvLog  # noqa: E402
from jssp.search_multi import CALL_FIELDS, SUMMARY_FIELDS, resolve_instance, search  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instances", nargs="+", help="ten bai (ft06, la01, ...) hoac duong dan file")
    ap.add_argument("--method", choices=["descent", "binary", "both"], default="both")
    ap.add_argument("--solver", default="cadical153")
    ap.add_argument("--per-call-timeout", type=float, default=600, help="giay cho MOI lan giai")
    ap.add_argument("--total-timeout", type=float, default=3600, help="giay cho CA lan tim (moi bai, moi cach)")
    ap.add_argument("--mem-limit-mb", type=float, default=None, help="vuot muc nay thi dung lan giai (MEMOUT)")
    ap.add_argument("--lb", type=int, default=None, help="can duoi lay tu tai lieu (duoc TIN, khong kiem chung)")
    ap.add_argument("--ub", type=int, default=None, help="can tren lay tu tai lieu (duoc kiem chung bang 1 lan giai)")
    ap.add_argument("--tiny", action="store_true", help="solver DPLL nho, chi de thu khi chua co PySAT")
    ap.add_argument("--out", default=str(ROOT / "results" / "raw"))
    args = ap.parse_args()

    out = Path(args.out)
    calls_log = CsvLog(out / "calls.csv", CALL_FIELDS)
    summary_log = CsvLog(out / "summary.csv", SUMMARY_FIELDS)
    methods = ["descent", "binary"] if args.method == "both" else [args.method]

    rows = []
    for name in args.instances:
        path = resolve_instance(name)
        for m in methods:
            print(f"\n=== {path.stem} | {m} | {'DPLL nho (--tiny)' if args.tiny else args.solver} ===")
            r = search(path, m, args.solver, args.lb, args.ub, args.per_call_timeout, args.total_timeout,
                       args.mem_limit_mb, args.tiny, calls_log, summary_log, ROOT / "results" / "schedules")
            rows.append(r)

    print("\n" + "=" * 78)
    print(f"{'bai':8s} {'cach':8s} {'ket qua':10s} {'LB':>6s} {'UB':>6s} {'so lan giai':>11s} {'giay':>9s}")
    for r in rows:
        verdict = f"toi uu {r.ub}" if r.optimal else r.status
        print(f"{r.instance:8s} {r.method:8s} {verdict:10s} {r.lb:6d} {r.ub:6d} {r.n_calls:11d} {r.total_time:9.1f}")
    print(f"\nDa ghi: {out / 'calls.csv'} va {out / 'summary.csv'}")
    return 0 if all(r.optimal for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
