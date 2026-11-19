"""Kiem thu T11: ket hop CP-SAT + Incremental SAT (bien the B, C).

Khong can PySAT / OR-Tools: SAT dung DPLL nho (tiny), CP-SAT khoi dong la ham GIA tra ve can va lich co san.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from jssp.hybrid import hybrid_solver_label, run_hybrid  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.runner import CsvLog  # noqa: E402
from jssp.search_multi import CALL_FIELDS, SUMMARY_FIELDS, search  # noqa: E402
from jssp.validate import validate_schedule  # noqa: E402
from test_cpsat import OPT55  # noqa: E402

FT06 = ROOT / "data" / "ft06.txt"


def serial_schedule(inst):
    """Lich hop le nhung rat dai: lam lan luot tung thao tac mot."""
    t, out = 0, []
    for job in inst.jobs:
        row = []
        for _, d in job:
            row.append(t)
            t += d
        out.append(row)
    return out


def rows_of(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


# ------------------------------------------------------------------ search() nhan lich ngoai
def test_search_uses_external_schedule_without_verification_call(tmp_path):
    summ = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    calls = CsvLog(tmp_path / "c.csv", CALL_FIELDS)
    r = search(FT06, "inc_binary", tiny=True, init_starts=OPT55, tag="hybrid_B", ub_label="CP-SAT",
               calls_log=calls, summary_log=summ, verbose=False)
    assert r.optimal and r.lb == r.ub == 55 and r.method == "hybrid_B"
    assert [c["L"] for c in r.calls] == [51, 53, 54]            # khong co lan hoi L=55 de xac nhan can tren
    s = rows_of(tmp_path / "s.csv")[0]
    assert s["method"] == "hybrid_B" and s["ub_init"] == "55" and s["ub_source"] == "CP-SAT"
    assert {c["method"] for c in rows_of(tmp_path / "c.csv")} == {"hybrid_B"}


def test_search_rejects_invalid_external_schedule():
    with pytest.raises(ValueError):
        search(FT06, "inc_binary", tiny=True, init_starts=[[0] * 6 for _ in range(6)], verbose=False)


def test_search_keeps_heuristic_if_external_schedule_is_worse(tmp_path):
    inst = read_instance(FT06)
    assert validate_schedule(inst, serial_schedule(inst)) == []
    summ = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    r = search(FT06, "inc_binary", tiny=True, init_starts=serial_schedule(inst), summary_log=summ, verbose=False)
    assert r.optimal and rows_of(tmp_path / "s.csv")[0]["ub_init"] == "59"      # lay heuristic 59, khong phai lich dai


# ------------------------------------------------------------------ run_hybrid
def make_cp(counter, **over):
    base = dict(lb=51, ub=55, optimal=False, status="TIMEOUT", total_time=10.0, best_starts=OPT55, peak_mem_mb=100.0)
    base.update(over)

    def fake_cp(path, budget, workers, seed, mem, summary_log, save_dir, verbose):
        counter.append(budget)
        return SimpleNamespace(**base)
    return fake_cp


def test_variants_b_and_c_share_warmup_and_c_needs_fewer_calls(tmp_path):
    out = tmp_path / "raw"
    seen = []
    summ = CsvLog(out / "summary.csv", SUMMARY_FIELDS)
    kw = dict(tiny=True, out_dir=out, summary_log=summ, run_cp=make_cp(seen), verbose=False)
    b = run_hybrid(FT06, "B", 60, **kw)
    c = run_hybrid(FT06, "C", 60, **kw)
    assert seen == [12.0]                                         # CP-SAT khoi dong chi chay 1 lan (20% cua 60s)
    assert (tmp_path / "warmup" / "ft06_cpsat-w1_12s.json").exists()
    for r in (b, c):
        assert r.optimal and r.lb == r.ub == 55 and r.total_time >= 10.0       # tinh ca thoi gian khoi dong
    assert (b.n_calls, c.n_calls) == (3, 2)                       # B: 51,53,54 ; C (lb=51): 53,54
    rows = rows_of(out / "summary.csv")
    assert [r["method"] for r in rows] == ["hybrid_B", "hybrid_C"]
    assert rows[0]["solver"] == hybrid_solver_label("cadical153", True, 1) == "DPLL-tiny+cpsat-w1"
    assert "max(SAT" in rows[0]["lb_source"] and "CP-SAT" in rows[1]["lb_source"]
    assert rows[0]["lb_init"] == "47" and rows[0]["ub_init"] == "59"                # cap ban dau cua CA quy trinh


def test_optimal_warmup_skips_sat_stage(tmp_path):
    out = tmp_path / "raw"
    summ = CsvLog(out / "summary.csv", SUMMARY_FIELDS)

    def boom(*a, **k):
        pytest.fail("khong duoc goi SAT khi CP-SAT da chung minh toi uu")

    r = run_hybrid(FT06, "B", 60, tiny=True, out_dir=out, summary_log=summ, run_sat=boom,
                   run_cp=make_cp([], lb=55, ub=55, optimal=True, status="OPTIMAL", total_time=7.0), verbose=False)
    assert r.optimal and r.n_calls == 0 and r.total_time == 7.0 and (r.lb, r.ub) == (55, 55)
    assert (tmp_path / "schedules" / "ft06_hybrid_B_DPLL-tiny+cpsat-w1.json").exists()


def test_sat_stage_gets_the_remaining_budget_and_bounds_are_merged(tmp_path):
    got = {}

    def fake_sat(path, method, solver, lb, ub, per_call, total, mem, tiny, calls_log, summ, save_dir, verbose,
                 init_starts=None, tag=None, lb_label=None, ub_label=None):
        got.update(method=method, lb=lb, ub=ub, per_call=per_call, total=total, tag=tag, init=init_starts)
        return SimpleNamespace(lb=49, ub=55, best_starts=OPT55, status="TIMEOUT", n_calls=2, total_time=70.0,
                               calls=[], peak_mem_mb=500.0)

    out = tmp_path / "raw"
    summ = CsvLog(out / "summary.csv", SUMMARY_FIELDS)
    r = run_hybrid(FT06, "B", 100, tiny=True, out_dir=out, summary_log=summ, run_sat=fake_sat,
                   run_cp=make_cp([], total_time=30.0), verbose=False)
    assert got["method"] == "inc_binary" and got["total"] == got["per_call"] == 70.0       # 100 - 30 khoi dong
    assert got["lb"] is None and got["ub"] is None and got["init"] == OPT55 and got["tag"] == "hybrid_B"
    assert (r.lb, r.ub, r.status, r.optimal) == (51, 55, "TIMEOUT", False)                # max(49, 51), min(55, 55)
    assert r.total_time == 100.0 and r.peak_mem_mb == 500.0
    c = run_hybrid(FT06, "C", 100, tiny=True, out_dir=out, run_sat=fake_sat, run_cp=make_cp([], total_time=30.0),
                   verbose=False)
    assert got["lb"] == 51                                                                  # bien the C truyen can duoi


def test_warmup_that_eats_the_whole_budget(tmp_path):
    r = run_hybrid(FT06, "C", 60, tiny=True, out_dir=tmp_path / "raw", run_cp=make_cp([], total_time=60.0),
                   run_sat=lambda *a, **k: pytest.fail("khong con ngan sach cho SAT"), verbose=False)
    assert r.status == "TIMEOUT" and (r.lb, r.ub) == (51, 55) and r.n_calls == 0


# ------------------------------------------------------------------ dong lenh
def run_cli(*args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "run_hybrid.py"), *args],
                          capture_output=True, text=True, timeout=60)


def test_cli_dry_run_and_resume_plan(tmp_path):
    r = run_cli("--instances", "ft06", "--dry-run", "--out", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert "B,C" in r.stdout and "toi da" in r.stdout and "3600s" in r.stdout
    with open(tmp_path / "summary.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["instance", "method", "solver", "status"])
        w.writeheader()
        w.writerow({"instance": "ft06", "method": "hybrid_B", "solver": "cadical153+cpsat-w1", "status": "TIMEOUT"})
    r = run_cli("--instances", "ft06", "--dry-run", "--out", str(tmp_path))
    assert r.returncode == 0 and "  C\n" in r.stdout and "B,C" not in r.stdout           # B da co: chi con C
