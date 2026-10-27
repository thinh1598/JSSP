"""Kiem thu ma hoa theo DAP AN DA BIET (nhiem vu T6): voi moi bai co toi uu da biet `opt`,
    - S_opt   phai THOA   (va lich giai ma hop le)
    - S_opt-1 phai KHONG THOA
Moi lan giai chay trong mot tien trinh rieng co gioi han thoi gian (qua gio = TIMEOUT, khong ket luan).

Chay (tu thu muc goc repo):
    python scripts/verify_known.py                          # ft06 + cac bai la01..la05, ft10 neu co file
    python scripts/verify_known.py --only ft06 ft10 --timeout 1800
    python scripts/verify_known.py --solver glucose4
Ket qua: results/small_check.csv va results/small_check.md (dua vao bao cao).
"""
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ["ft06", "la01", "la02", "la03", "la04", "la05", "ft10"]


def find_instance(name: str):
    for p in (ROOT / "data" / f"{name}.txt", ROOT / "data" / "instances" / f"{name}.txt"):
        if p.exists():
            return p
    return None


def run_case(path: Path, L: int, solver: str, tiny: bool, timeout: float) -> dict:
    cmd = [sys.executable, str(ROOT / "scripts" / "run_sat.py"), str(path), "--L", str(L),
           "--solver", solver, "--json"] + (["--tiny"] if tiny else [])
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "time": time.perf_counter() - t0}
    dt = time.perf_counter() - t0
    if p.returncode != 0 or not p.stdout.strip():
        return {"status": "ERROR", "time": dt, "detail": (p.stderr or p.stdout).strip()[-400:]}
    out = json.loads(p.stdout.strip().splitlines()[-1])
    out["time"] = dt
    return out


def verdict(expected: str, r: dict) -> str:
    got = r["status"]
    if got == expected and (expected == "UNSAT" or r.get("valid")):
        return "PASS"
    if got == "TIMEOUT":
        return "TIMEOUT (chua ket luan)"
    if got == "ERROR":
        return "ERROR"
    if expected == "SAT" and got == "UNSAT":
        return "MISMATCH: UNSAT du dap an da biet la kha thi -> nghi LOI MA HOA, can dieu tra"
    if expected == "UNSAT" and got == "SAT":
        return "MISMATCH: co lich NGAN HON dap an da biet (da qua validate) -> kiem tra lai gia tri trong known_bounds.csv"
    return f"MISMATCH ({got}, valid={r.get('valid')})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="chi chay cac bai nay (mac dinh: " + " ".join(DEFAULT) + ")")
    ap.add_argument("--solver", default="cadical153")
    ap.add_argument("--timeout", type=float, default=600, help="gioi han giay cho MOI lan giai")
    ap.add_argument("--tiny", action="store_true", help="dung solver DPLL nho (chi de thu khi chua co PySAT)")
    args = ap.parse_args()

    known = {}
    with open(ROOT / "data" / "known_bounds.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["status"] == "optimal":
                known[row["instance"]] = int(row["lb"])

    rows, bad = [], 0
    for name in (args.only or DEFAULT):
        path = find_instance(name)
        if path is None:
            print(f"[bo qua] {name}: khong co file du lieu (chay scripts/fetch_benchmarks.py)")
            continue
        if name not in known:
            print(f"[bo qua] {name}: khong co toi uu da biet trong data/known_bounds.csv")
            continue
        opt = known[name]
        for L, expected in ((opt, "SAT"), (opt - 1, "UNSAT")):
            r = run_case(path, L, args.solver, args.tiny, args.timeout)
            v = verdict(expected, r)
            bad += v.startswith(("MISMATCH", "ERROR"))
            rows.append({"instance": name, "known_opt": opt, "L": L, "expected": expected,
                         "got": r["status"], "valid_schedule": "" if r.get("valid") is None else r["valid"],
                         "vars": r.get("vars", ""), "clauses": r.get("clauses", ""),
                         "seconds": round(r["time"], 2), "verdict": v})
            print(f"{name:6s} L={L:<5d} mong doi {expected:5s} -> {r['status']:8s} {r['time']:8.1f}s  {v}")
            if r["status"] == "ERROR":
                print("   ", r.get("detail", ""))

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    if rows:
        with open(out / "small_check.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        lines = ["# Bao cao kiem thu nho (ma hoa Crawford vs dap an da biet)", "",
                 f"Solver: {'DPLL nho' if args.tiny else args.solver}; gioi han {args.timeout:.0f}s moi lan giai.", "",
                 "| bai | toi uu da biet | L | mong doi | ket qua | lich hop le | bien | clause | giay | danh gia |",
                 "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            lines.append("| " + " | ".join(str(r[k]) for k in (
                "instance", "known_opt", "L", "expected", "got", "valid_schedule", "vars", "clauses",
                "seconds", "verdict")) + " |")
        (out / "small_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nDa ghi {out / 'small_check.md'} va small_check.csv")
    print("\nTONG KET:", "CO LOI/BAT THUONG - xem cac dong MISMATCH/ERROR" if bad else
          "khong co mau thuan (TIMEOUT neu co = chua ket luan, khong phai loi)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
