"""Kiem thu T9: baseline CP-SAT.

Phan 1 (luon chay): logic cua khung chay (quy doi trang thai, kiem tra lai lich, ghi CSV) bang tien trinh con GIA,
        nen khong can cai OR-Tools.
Phan 2 (can `pip install ortools`, tu bo qua neu chua cai): giai that va doi chieu voi phep vet can va dap an FT06 = 55.
"""
import csv
import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import jssp.baselines as bl  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.runner import CsvLog, RunInfo  # noqa: E402
from jssp.search_multi import SUMMARY_FIELDS  # noqa: E402
from jssp.validate import makespan, validate_schedule  # noqa: E402

FT06 = ROOT / "data" / "ft06.txt"
OPT55 = [[22, 27, 30, 36, 43, 49], [0, 8, 13, 28, 40, 50], [0, 5, 9, 18, 27, 30],
         [8, 13, 23, 28, 37, 46], [13, 22, 25, 38, 50, 54], [13, 16, 19, 30, 45, 49]]   # lich toi uu 55 cua FT06


def fake_child(monkeypatch, payload=None, status="OK", returncode=0, stderr=""):
    """Thay tien trinh con that bang mot ket qua dung san."""
    out = "" if payload is None else json.dumps(payload) + "\n"
    monkeypatch.setattr(bl, "run_with_limits",
                        lambda cmd, timeout=None, mem_limit_mb=None, poll=0.05:
                        RunInfo(status, returncode if status == "OK" else None, out, stderr, 1.5, 123.4))


def test_the_known_schedule_is_valid():
    inst = read_instance(FT06)
    assert validate_schedule(inst, OPT55, 55) == [] and makespan(inst, OPT55) == 55


def test_optimal_is_accepted_and_logged(monkeypatch, tmp_path):
    fake_child(monkeypatch, {"status": "OPTIMAL", "makespan": 55, "best_bound": 54.9999999, "starts": OPT55})
    log = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    r = bl.run_cpsat(FT06, time_limit=10, summary_log=log, save_dir=tmp_path / "sch", verbose=False)
    assert r.optimal and r.status == "OPTIMAL" and r.lb == r.ub == 55 and r.n_calls == 1
    row = list(csv.DictReader(open(tmp_path / "s.csv", encoding="utf-8")))[0]
    assert row["method"] == "cpsat" and row["solver"] == "cpsat-w1" and row["optimal"] == "True"
    assert row["lb_init"] == "47" and row["ub_init"] == "59" and row["max_peak_mem_mb"] == "123.4"
    assert (tmp_path / "sch" / "ft06_cpsat_cpsat-w1.json").exists()


def test_feasible_at_time_limit_reports_interval(monkeypatch):
    fake_child(monkeypatch, {"status": "FEASIBLE", "makespan": 55, "best_bound": 50.3, "starts": OPT55})
    r = bl.run_cpsat(FT06, verbose=False)
    assert r.status == "TIMEOUT" and not r.optimal and (r.lb, r.ub) == (51, 55)     # lb = tran cua 50.3


def test_unknown_keeps_heuristic_upper_bound(monkeypatch):
    fake_child(monkeypatch, {"status": "UNKNOWN", "makespan": None, "best_bound": 49.0, "starts": None})
    r = bl.run_cpsat(FT06, verbose=False)
    assert r.status == "TIMEOUT" and (r.lb, r.ub) == (49, 59)
    assert validate_schedule(read_instance(FT06), r.best_starts) == []              # van co lich that kem theo


def test_invalid_schedule_from_child_is_rejected(monkeypatch):
    bad = [[0] * 6 for _ in range(6)]
    fake_child(monkeypatch, {"status": "OPTIMAL", "makespan": 55, "best_bound": 55.0, "starts": bad})
    r = bl.run_cpsat(FT06, verbose=False)
    assert r.status == "ERROR" and not r.optimal


@pytest.mark.parametrize("kwargs,expected", [
    ({"status": "TIMEOUT"}, "TIMEOUT"),
    ({"status": "MEMOUT"}, "MEMOUT"),
    ({"returncode": 1, "stderr": "boom"}, "ERROR"),
    ({"payload": {"status": "INFEASIBLE", "best_bound": 0, "starts": None}}, "ERROR"),
])
def test_other_outcomes(monkeypatch, kwargs, expected):
    fake_child(monkeypatch, **kwargs)
    r = bl.run_cpsat(FT06, verbose=False)
    assert r.status == expected and not r.optimal and (r.lb, r.ub) == (47, 59)


def test_no_solver_call_when_heuristic_hits_lower_bound(monkeypatch, tmp_path):
    p = tmp_path / "one.txt"
    p.write_text("1 2\n0 3 1 4\n", encoding="utf-8")                                 # 1 job: toi uu = 7 = can duoi
    monkeypatch.setattr(bl, "run_with_limits", lambda *a, **k: pytest.fail("khong duoc goi solver"))
    r = bl.run_cpsat(p, verbose=False)
    assert r.optimal and r.lb == r.ub == 7 and r.n_calls == 0


# ------------------------------------------------------------------ giai that (can OR-Tools)
def test_real_cpsat_ft06():
    pytest.importorskip("ortools")
    from jssp.cpsat import solve_cpsat
    inst = read_instance(FT06)
    r = solve_cpsat(inst, inst.trivial_lower_bound(), 59, time_limit=60, workers=1)
    assert r["status"] == "OPTIMAL" and r["makespan"] == 55
    assert validate_schedule(inst, r["starts"], 55) == []


def test_real_cpsat_matches_brute_force_on_random_tiny():
    pytest.importorskip("ortools")
    from jssp.cpsat import solve_cpsat
    from jssp.heuristic import best_greedy
    from test_crawford import brute_force_optimum
    from test_search import random_tiny
    rng = random.Random(3)
    for _ in range(8):
        inst = random_tiny(rng)
        ub = makespan(inst, best_greedy(inst))
        r = solve_cpsat(inst, inst.trivial_lower_bound(), ub, time_limit=30)
        assert r["status"] == "OPTIMAL" and r["makespan"] == brute_force_optimum(inst)
        assert validate_schedule(inst, r["starts"], ub) == []


def test_real_end_to_end_subprocess(tmp_path):
    pytest.importorskip("ortools")
    log = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    r = bl.run_cpsat(FT06, time_limit=60, summary_log=log, verbose=False)
    assert r.optimal and r.lb == r.ub == 55
    assert list(csv.DictReader(open(tmp_path / "s.csv", encoding="utf-8")))[0]["method"] == "cpsat"
