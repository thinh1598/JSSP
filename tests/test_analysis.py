"""Kiem thu T14: gop ket qua (analysis.py): dong moi nhat, bang, tong hop, kiem tra nhat quan."""
import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp import analysis as an  # noqa: E402

FIELDS = ["timestamp", "instance", "n_jobs", "n_machines", "method", "solver", "lb_init", "lb_source", "ub_init",
          "ub_source", "lb_final", "ub_final", "optimal", "status", "n_calls", "total_time", "max_peak_mem_mb"]


def mk(inst, method, solver, lb, ub, optimal, time, lb_init=100, ub_init=200, status=None, n_calls=1, mem=50.0,
       ts="2026-11-01 00:00:00", size=(10, 10)):
    return {"timestamp": ts, "instance": inst, "n_jobs": size[0], "n_machines": size[1], "method": method,
            "solver": solver, "lb_init": lb_init, "lb_source": "x", "ub_init": ub_init, "ub_source": "y",
            "lb_final": lb, "ub_final": ub, "optimal": optimal,
            "status": status or ("OPTIMAL" if optimal else "TIMEOUT"), "n_calls": n_calls, "total_time": time,
            "max_peak_mem_mb": mem}


def write(tmp_path, rows):
    p = tmp_path / "summary.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return p


def test_latest_row_wins_and_replacements_are_counted(tmp_path):
    p = write(tmp_path, [mk("ft10", "cpo", "cpo-w1", 930, 930, True, 9.0, ts="a"),
                         mk("ft10", "cpo", "cpo-w1", 930, 930, True, 4.0, ts="b"),
                         mk("ft10", "cpsat", "cpsat-w1", 930, 930, True, 40.0)])
    rows, replaced = an.load_rows(p)
    assert replaced == 1 and len(rows) == 2
    assert rows[("ft10", "cpo", "cpo-w1")].time == 4.0


def test_cell_text_formats():
    base = dict(instance="a", n_jobs=1, n_machines=1, method="m", solver="s", lb_init=1, ub_init=9, n_calls=1,
                mem=None, timestamp="t")
    R = lambda **k: an.Row(**{**base, **k})                                         # noqa: E731
    assert an.cell_text(None) == "-"
    assert an.cell_text(R(lb=5, ub=5, optimal=True, status="OPTIMAL", time=12.34)) == "12.3"
    assert an.cell_text(R(lb=5, ub=8, optimal=False, status="TIMEOUT", time=900)) == "[5, 8]"
    assert an.cell_text(R(lb=5, ub=8, optimal=False, status="MEMOUT", time=3)) == "het RAM"
    assert an.cell_text(R(lb=5, ub=8, optimal=False, status="ERROR", time=3)) == "loi"


def test_winner_rule():
    base = dict(instance="a", n_jobs=1, n_machines=1, lb_init=1, ub_init=9, n_calls=1, mem=None, timestamp="t")
    R = lambda m, lb, ub, opt, t: an.Row(**base, method=m, solver="s", lb=lb, ub=ub, optimal=opt,        # noqa: E731
                                         status="OPTIMAL" if opt else "TIMEOUT", time=t)
    cells = {("x", "s"): R("x", 5, 5, True, 10), ("y", "s"): R("y", 5, 5, True, 3), ("z", "s"): R("z", 1, 8, False, 900)}
    assert an.winner(cells) == ("y", "s")                              # nhanh nhat trong cac cach chung minh duoc
    cells = {("x", "s"): R("x", 3, 8, False, 900), ("y", "s"): R("y", 5, 7, False, 900)}
    assert an.winner(cells) == ("y", "s")                              # khong ai xong: can tren nho hon
    cells = {("x", "s"): R("x", 3, 7, False, 900), ("y", "s"): R("y", 5, 7, False, 900)}
    assert an.winner(cells) == ("y", "s")                              # hoa can tren: can duoi lon hon
    cells = {("x", "s"): R("x", 5, 7, False, 900), ("y", "s"): R("y", 5, 7, False, 900)}
    assert an.winner(cells) is None                                    # hoa hoan toan: khong in dam


def test_table_and_markdown_and_latex(tmp_path):
    p = write(tmp_path, [mk("ft10", "cpo", "cpo-w1", 930, 930, True, 4.4), mk("ft10", "cpsat", "cpsat-w1", 930, 930, True, 39.7),
                         mk("la21", "cpo", "cpo-w1", 1046, 1046, True, 37.5, size=(15, 10)),
                         mk("la21", "cpsat", "cpsat-w1", 1033, 1046, False, 900, size=(15, 10))])
    rows, _ = an.load_rows(p)
    t = an.comparison_table(rows, an.MAIN_COLS)
    assert t[0][:2] == ["bai", "co"] and [r[0] for r in t[1:]] == ["ft10", "la21"]
    cpo_col = t[0].index("CP Optimizer")
    assert t[1][cpo_col] == "4.4" and t[2][t[0].index("CP-SAT")] == "[1033, 1046]" and t[1][t[0].index("Gurobi MIP")] == "-"
    bold = an._bold_flags(rows, an.MAIN_COLS, ["ft10", "la21"])
    md = an.to_markdown(t, bold)
    assert "**4.4**" in md and "**37.5**" in md and "**39.7**" not in md
    tex = an.to_latex(t, bold, caption="c", label="tab:x")
    assert r"\toprule" in tex and r"\textbf{4.4}" in tex and "{[}1033, 1046{]}" in tex and r"\label{tab:x}" in tex


def test_trivial_instances_are_excluded_from_summary(tmp_path):
    p = write(tmp_path, [mk("la05", "cpo", "cpo-w1", 593, 593, True, 0.01, lb_init=593, ub_init=593, n_calls=0),
                         mk("ft10", "cpo", "cpo-w1", 930, 930, True, 10.0),
                         mk("ft06", "cpo", "cpo-w1", 55, 55, True, 2.0)])
    rows, _ = an.load_rows(p)
    s = [r for r in an.summary_by_method(rows, an.MAIN_COLS) if r["tier"] == "small" and r["method"] == "CP Optimizer"][0]
    assert s["n"] == 2 and s["solved"] == 2 and s["par2_s"] == 6.0           # (10 + 2) / 2, khong tinh la05


def test_par2_penalises_unsolved_with_twice_the_budget(tmp_path):
    p = write(tmp_path, [mk("la21", "cpsat", "cpsat-w1", 1033, 1046, False, 900, size=(15, 10)),
                         mk("la11", "cpsat", "cpsat-w1", 1222, 1222, True, 100, size=(20, 5))])
    rows, _ = an.load_rows(p)
    s = [r for r in an.summary_by_method(rows, an.MAIN_COLS) if r["tier"] == "medium"][0]
    assert s["n"] == 2 and s["solved"] == 1 and s["par2_s"] == (1800 + 100) / 2
    assert s["mean_gap_unsolved_pct"] == round(100 * 13 / 1033, 2)


def test_best_bounds(tmp_path):
    p = write(tmp_path, [mk("la21", "inc_binary", "cadical153", 1034, 1053, False, 900, size=(15, 10)),
                         mk("la21", "cpsat", "cpsat-w1", 1033, 1046, False, 900, size=(15, 10)),
                         mk("la21", "cpo", "cpo-w1", 1046, 1046, True, 37.5, size=(15, 10))])
    rows, _ = an.load_rows(p)
    b = an.best_bounds(rows)[0]
    assert (b["best_lb"], b["best_ub"], b["proven_optimal"]) == (1046, 1046, True)
    assert b["fastest_proof"].startswith("CP Optimizer 37.5") and b["best_lb_by"] == "(da toi uu)"


def test_best_bounds_lists_all_tied_methods_when_unsolved(tmp_path):
    p = write(tmp_path, [mk("abz8", "inc_binary", "cadical153", 626, 685, False, 3600, size=(20, 15)),
                         mk("abz8", "cpsat", "cpsat-w1", 597, 679, False, 3600, size=(20, 15)),
                         mk("abz8", "cpo", "cpo-w1", 600, 679, False, 3600, size=(20, 15))])
    rows, _ = an.load_rows(p)
    b = an.best_bounds(rows)[0]
    assert (b["best_lb"], b["best_lb_by"]) == (626, "Inc. SAT")
    assert (b["best_ub"], b["best_ub_by"]) == (679, "CP Optimizer / CP-SAT")


# ---------------------------------------------------------------- kiem tra nhat quan
def kinds(msgs):
    return [m for m in msgs if m[0] == "LOI"], [m for m in msgs if m[0] != "LOI"]


def test_consistency_clean_data_has_no_errors(tmp_path):
    p = write(tmp_path, [mk("la21", "inc_binary", "cadical153", 1034, 1053, False, 900, size=(15, 10)),
                         mk("la21", "cpo", "cpo-w1", 1046, 1046, True, 37.5, size=(15, 10)),
                         mk("la21", "cpsat", "cpsat-w1", 1033, 1046, False, 900, size=(15, 10))])
    rows, _ = an.load_rows(p)
    assert kinds(an.check_consistency(rows)) == ([], [])


def test_consistency_detects_lb_above_other_solvers_ub(tmp_path):
    p = write(tmp_path, [mk("la21", "inc_binary", "cadical153", 1050, 1060, False, 900, size=(15, 10)),
                         mk("la21", "cpsat", "cpsat-w1", 1033, 1046, False, 900, size=(15, 10))])
    rows, _ = an.load_rows(p)
    errs, _ = kinds(an.check_consistency(rows))
    assert len(errs) == 1 and "1050" in errs[0][1] and "1046" in errs[0][1]


def test_consistency_detects_two_different_optima_and_bad_flags(tmp_path):
    p = write(tmp_path, [mk("abz5", "cpo", "cpo-w1", 1234, 1234, True, 3), mk("abz5", "cpsat", "cpsat-w1", 1230, 1230, True, 80),
                         mk("abz6", "gurobi", "gurobi-t1", 940, 943, True, 5),            # toi uu nhung LB != UB
                         mk("orb01", "cpo", "cpo-w1", 1060, 1059, False, 900)])           # LB > UB
    rows, _ = an.load_rows(p)
    errs, _ = kinds(an.check_consistency(rows))
    text = "\n".join(m for _, m in errs)
    assert "khac nhau" in text and "danh dau toi uu" in text and "1060 > can tren 1059" in text


def test_consistency_checks_against_known_optimum(tmp_path):
    p = write(tmp_path, [mk("ft10", "cpo", "cpo-w1", 931, 931, True, 5)])
    rows, _ = an.load_rows(p)
    known = {"ft10": (930, 930, "optimal")}
    errs, _ = kinds(an.check_consistency(rows, known))
    assert any("tai lieu" in m for _, m in errs)
    known_open = {"ft10": (900, 960, "open_2010")}
    assert kinds(an.check_consistency(rows, known_open))[0] == []


def test_consistency_warns_about_sleep_and_early_timeouts(tmp_path):
    p = write(tmp_path, [mk("yn1", "gurobi", "gurobi-t1", 694, 1005, False, 5565.2, size=(20, 20)),
                         mk("abz5", "cplex", "cplex-t1", 1077, 1240, False, 10.3),
                         mk("la21", "cpsat", "cpsat-w1", 1033, 1046, False, 903.4, size=(15, 10))])
    rows, _ = an.load_rows(p)
    errs, warns = kinds(an.check_consistency(rows))
    assert errs == []
    text = "\n".join(m for _, m in warns)
    assert "yn1/gurobi" in text and "vuot ngan sach" in text and "abz5/cplex" in text and "la21" not in text


def test_zero_calls_only_warned_for_baselines_not_sat(tmp_path):
    p = write(tmp_path, [mk("abz7", "inc_binary", "cadical153", 556, 769, False, 3600, n_calls=0, size=(20, 15)),
                         mk("abz7", "cpsat", "cpsat-w1", 651, 665, False, 3600, n_calls=0, size=(20, 15))])
    rows, _ = an.load_rows(p)
    _, warns = kinds(an.check_consistency(rows))
    assert len(warns) == 1 and "abz7/cpsat" in warns[0][1]


def test_cactus_data_sorted_and_excludes_trivial(tmp_path):
    p = write(tmp_path, [mk("ft06", "cpo", "cpo-w1", 55, 55, True, 3.0), mk("ft10", "cpo", "cpo-w1", 930, 930, True, 1.0),
                         mk("la05", "cpo", "cpo-w1", 593, 593, True, 0.01, lb_init=593, ub_init=593)])
    rows, _ = an.load_rows(p)
    c = [r for r in an.cactus_data(rows, an.MAIN_COLS) if r["method"] == "CP Optimizer"]
    assert [(r["solved"], r["time_s"]) for r in c] == [(1, 1.0), (2, 3.0)]


def test_script_end_to_end_and_exit_code(tmp_path):
    ok = write(tmp_path, [mk("ft10", "cpo", "cpo-w1", 930, 930, True, 4.0)])
    out = tmp_path / "an"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "analyze.py"), "--summary", str(ok),
                        "--known", str(tmp_path / "none.csv"), "--out", str(out)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    for f in ("table_main.md", "table_main.tex", "table_main.csv", "summary_by_method.csv", "best_bounds.csv", "consistency.txt"):
        assert (out / f).exists()
    assert "Khong co mau thuan" in (out / "consistency.txt").read_text(encoding="utf-8")
    bad = write(tmp_path, [mk("ft10", "cpo", "cpo-w1", 931, 931, True, 4.0), mk("ft10", "cpsat", "cpsat-w1", 930, 930, True, 9.0)])
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "analyze.py"), "--summary", str(bad),
                        "--known", str(tmp_path / "none.csv"), "--out", str(out)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 1 and "LOI" in (out / "consistency.txt").read_text(encoding="utf-8")
