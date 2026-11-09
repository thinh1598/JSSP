"""Kiem thu T10: chay hang loat (ke hoach, bo qua o da chay, gioi han gio phien, tiep tuc sau khi bi ngat).

Dung solver DPLL nho (tiny) cho phan SAT va CP-SAT GIA, nen khong can PySAT / OR-Tools.
"""
import csv
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.suite import (Cell, build_plan, load_done, run_suite, solver_label)  # noqa: E402

FT06 = ROOT / "data" / "ft06.txt"


def write_summary(path, rows):
    cols = ["instance", "method", "solver", "status"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def test_solver_label_matches_what_runners_write():
    assert solver_label("binary", "cadical153", False, 1) == "cadical153"
    assert solver_label("inc_binary", "glucose4", False, 1) == "glucose4"
    assert solver_label("binary", "cadical153", True, 1) == "DPLL-tiny"
    assert solver_label("cpsat", "cadical153", False, 8) == "cpsat-w8"


def test_plan_skips_done_cells_and_supports_retry_and_force(tmp_path):
    f = tmp_path / "summary.csv"
    write_summary(f, [
        {"instance": "ft06", "method": "binary", "solver": "cadical153", "status": "OPTIMAL"},
        {"instance": "ft06", "method": "cpsat", "solver": "cpsat-w1", "status": "TIMEOUT"},
    ])
    done = load_done(f)
    assert done[("ft06", "binary", "cadical153")] == ["OPTIMAL"]
    methods = ["binary", "inc_binary", "cpsat"]
    plan = {c.method: c for c in build_plan([FT06], methods, "cadical153", False, 1, done)}
    assert not plan["binary"].run and plan["inc_binary"].run and not plan["cpsat"].run     # TIMEOUT cung tinh la da co
    plan = {c.method: c for c in build_plan([FT06], methods, "cadical153", False, 1, done, retry_incomplete=True)}
    assert not plan["binary"].run and plan["inc_binary"].run and plan["cpsat"].run         # chi chay lai o chua OPTIMAL
    plan = build_plan([FT06], methods, "cadical153", False, 1, done, force=True)
    assert all(c.run for c in plan)
    assert plan[0].size == "6x6" and plan[0].name == "ft06"


def test_load_done_missing_file(tmp_path):
    assert load_done(tmp_path / "khong_co.csv") == {}


def test_max_seconds_stops_before_next_cell():
    ran = []
    cells = [Cell(FT06, "ft06", "6x6", m, m, True, "x") for m in ("binary", "inc_binary", "cpsat")]
    t = {"now": 0.0}

    def clock():
        return t["now"]

    def fake_sat(path, method, *a):
        ran.append(method)
        t["now"] += 100                                         # moi o "ton" 100 giay
        return SimpleNamespace(method=method)

    results, stopped = run_suite(cells, 60, max_seconds=150, clock=clock, run_sat=fake_sat,
                                 run_cp=lambda *a: ran.append("cpsat"), say=lambda s: None,
                                 out_dir=Path("/tmp/khong_ghi_gi"))
    assert ran == ["binary", "inc_binary"] and stopped          # sau 2 o da 200s >= 150s nen khong chay cpsat
    assert [r.method for r in results] == ["binary", "inc_binary"]


def test_resume_after_real_run(tmp_path):
    out = tmp_path / "raw"

    def fake_cp(path, budget, workers, seed, mem, summary_log, save_dir, verbose):
        summary_log.append({"instance": "ft06", "method": "cpsat", "solver": f"cpsat-w{workers}",
                            "status": "OPTIMAL"})
        return SimpleNamespace(method="cpsat")

    methods = ["binary", "inc_binary", "cpsat"]
    cells = build_plan([FT06], methods, "cadical153", True, 1, load_done(out / "summary.csv"))
    results, stopped = run_suite(cells, 60, tiny=True, out_dir=out, run_cp=fake_cp, say=lambda s: None)
    assert len(results) == 3 and not stopped
    rows = list(csv.DictReader(open(out / "summary.csv", encoding="utf-8")))
    assert [(r["method"], r["status"]) for r in rows] == [("binary", "OPTIMAL"), ("inc_binary", "OPTIMAL"),
                                                          ("cpsat", "OPTIMAL")]
    assert rows[0]["ub_final"] == "55" and rows[1]["ub_final"] == "55"          # SAT that (DPLL nho) ra dung 55
    # chay lai cung lenh: moi o da co => khong con gi de chay
    again = build_plan([FT06], methods, "cadical153", True, 1, load_done(out / "summary.csv"))
    assert not any(c.run for c in again)
    assert run_suite(again, 60, tiny=True, out_dir=out, run_cp=fake_cp, say=lambda s: None) == ([], False)


def test_cli_dry_run_runs_nothing(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_suite.py"), "--instances", "ft06",
                        "--methods", "binary,cpsat", "--dry-run", "--out", str(tmp_path)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "CHAY" in r.stdout and "6x6" in r.stdout and "toi da" in r.stdout
    assert not (tmp_path / "summary.csv").exists()
