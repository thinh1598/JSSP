"""Kiem thu T12: baseline CPLEX (CP Optimizer qua docplex, MIP qua file .lp + cplex.exe).

Phan 1 (luon chay): sinh file .lp doi chieu voi mo hinh mip.py (da kiem chung bang vet can); doc ket qua cplex.exe tu van ban
        mau; ham quy doi trang thai; khung chay bang tien trinh con GIA; docplex GIA va cplex.exe GIA.
Phan 2 (can Studio that, tu bo qua neu khong co): giai that va doi chieu voi phep vet can va FT06 = 55.
"""
import csv
import importlib.util
import json
import random
import re
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import jssp.baselines as bl  # noqa: E402
import jssp.cplex_mip as cm  # noqa: E402
import jssp.studio as studio  # noqa: E402
from jssp.cpo import map_cpo_status  # noqa: E402
from jssp.heuristic import best_greedy  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.mip import CMAX, build_mip  # noqa: E402
from jssp.runner import CsvLog  # noqa: E402
from jssp.search_multi import SUMMARY_FIELDS, resolve_instance  # noqa: E402
from jssp.suite import Cell, run_suite, solver_label  # noqa: E402
from jssp.validate import makespan, validate_schedule  # noqa: E402
from test_cpsat import FT06, OPT55, fake_child  # noqa: E402
from test_crawford import HAND, brute_force_optimum, make  # noqa: E402
from test_search import random_tiny  # noqa: E402


# ------------------------------------------------------------------ file .lp phai khop dung mo hinh mip.py
def parse_lp(text):
    """Doc lai file .lp do cm.lp_text sinh ra (chi dinh dang ma ta sinh)."""
    rows, bounds, general, binary, section = [], {}, [], [], None
    for ln in text.splitlines():
        if not ln.strip() or ln.startswith("\\"):
            continue
        if ln in ("Minimize", "Subject To", "Bounds", "General", "Binary", "End"):
            section = ln
            continue
        if section == "Subject To":
            m = re.match(r" c(\d+): (.*) >= (-?\d+)$", ln)
            assert m, ln
            toks = m.group(2).split()
            coef, sign, i = {}, 1, 0
            while i < len(toks):
                t = toks[i]
                if t in "+-":
                    sign = 1 if t == "+" else -1
                    i += 1
                    continue
                if re.fullmatch(r"\d+", t):                     # he so, ten bien o sau
                    coef[toks[i + 1]] = sign * int(t)
                    i += 2
                else:
                    coef[t] = sign
                    i += 1
                sign = 1
            rows.append((coef, int(m.group(3))))
        elif section == "Bounds":
            lo, _, name, _, hi = ln.split()
            bounds[name] = (int(lo), int(hi))
        elif section == "General":
            general += ln.split()
        elif section == "Binary":
            binary += ln.split()
    return rows, bounds, general, binary


def check_lp_matches_spec(inst, lb, ub):
    spec = build_mip(inst, lb, ub)
    text = cm.lp_text(spec)
    rows, bounds, general, binary = parse_lp(text)
    assert len(rows) == len(spec.cons)
    for (coef, rhs), k in zip(rows, spec.cons):
        want = {cm._vname(k.x): 1, cm._vname(k.w): -1}
        if k.ykey is not None and k.coef != 0:
            want[cm._yname(k.ykey)] = -k.coef                      # s_x - s_w - coef*y >= c
        assert coef == want and rhs == k.c
    for a in spec.ops:
        assert bounds[cm._vname(a)] == (spec.lo[a], spec.hi[a])
    assert bounds[cm.CNAME] == (spec.lo[CMAX], spec.hi[CMAX])
    assert sorted(general) == sorted([cm._vname(a) for a in spec.ops] + [cm.CNAME])
    assert sorted(binary) == sorted(cm._yname(k) for k in spec.ykeys)
    assert max(len(ln) for ln in text.splitlines()) < 300         # LP gioi han ~560 ky tu/dong
    names = set(general) | set(binary)
    assert len(names) == len(general) + len(binary)                # khong trung ten bien
    return text


def test_lp_matches_model_on_ft06_and_tiny():
    check_lp_matches_spec(read_instance(FT06), 47, 59)
    check_lp_matches_spec(make(HAND), 6, 10)
    rng = random.Random(2)
    for _ in range(10):
        inst = random_tiny(rng)
        check_lp_matches_spec(inst, inst.trivial_lower_bound(), makespan(inst, best_greedy(inst)))


def test_variable_names_are_safe_for_lp_format():
    text = check_lp_matches_spec(read_instance(FT06), 47, 59)
    names = re.findall(r"\b[A-Za-z_][\w.]*\b", text.split("Bounds")[1])
    reserved = {"Bounds", "General", "Binary", "End", "inf", "infinity", "free"}
    assert not [n for n in names if n.lower() in {r.lower() for r in reserved} - {"bounds", "general", "binary", "end"}]
    assert all(n[0] in "smy" for n in names if n not in reserved)      # s_.., y_.., mksp: khong bat dau bang e/E (de nham so mu)


# ------------------------------------------------------------------ doc ket qua cplex.exe
def test_parse_status_from_sample_logs():
    assert cm.parse_status("MIP - Integer optimal solution:  Objective =  7.5000000000e+02", True) == "OPTIMAL"
    assert cm.parse_status("MIP - Time limit exceeded, integer feasible:  Objective = 1.0e+03", True) == "FEASIBLE"
    assert cm.parse_status("MIP - Time limit exceeded, no integer solution.", False) == "UNKNOWN"
    assert cm.parse_status("MIP - Integer infeasible.", False) == "INFEASIBLE"
    assert cm.parse_status("CPLEX Error  1016: Community Edition. Problem size limits exceeded.", False) == "LICENSE_LIMIT"
    assert cm.parse_status("MIP - Memory limit exceeded", True) == "FEASIBLE"


def test_parse_best_bound_takes_last_and_handles_formats():
    assert cm.parse_best_bound("x\nCurrent MIP best bound =  9.3500000000e+02 (gap = 129.0, 12.12%)") == 935.0
    assert cm.parse_best_bound("Current MIP best bound = 900 (gap = 1)\nCurrent MIP best bound = 1.0e+03 (gap = 0)") == 1000.0
    assert cm.parse_best_bound("khong co dong nao") is None


def sol_xml(values):
    vs = "\n".join(f'  <variable name="{k}" index="{i}" value="{v}" reducedCost="0"/>' for i, (k, v) in enumerate(values.items()))
    return ('<?xml version="1.0" standalone="yes"?>\n<CPLEXSolution version="1.2">\n'
            ' <header problemName="model" objectiveValue="55" solutionTypeValue="3"/>\n'
            f' <variables>\n{vs}\n </variables>\n</CPLEXSolution>\n')


def opt55_values():
    vals = {f"s_{l}_{i}": OPT55[l][i] for l in range(6) for i in range(6)}
    vals[cm.CNAME] = 55
    return vals


def test_parse_sol_values():
    v = cm.parse_sol_values(sol_xml({"s_0_0": 3, "y_0_0_1_1": "1.0000000000000002", "mksp": "5.5e+01"}))
    assert v == {"s_0_0": 3.0, "y_0_0_1_1": 1.0000000000000002, "mksp": 55.0}


# ------------------------------------------------------------------ cplex.exe GIA
def fake_cplex(monkeypatch, out_text, values=None, record=None):
    monkeypatch.setattr(cm, "find_exe", lambda kind: "C:/fake/cplex.exe")

    def fake_run(cmd, input=None, capture_output=None, text=None, **kw):
        if record is not None:
            record["input"], record["cmd"] = input, cmd
        m = re.search(r"write (\S+\.sol)", input)
        lp = re.search(r"read (\S+\.lp)", input).group(1)
        assert Path(lp).exists() and "Minimize" in Path(lp).read_text()      # file .lp da duoc ghi truoc khi goi
        if values is not None:
            Path(m.group(1)).write_text(sol_xml(values), encoding="utf-8")
        return SimpleNamespace(stdout=out_text, stderr="", returncode=0)

    monkeypatch.setattr(cm.subprocess, "run", fake_run)


def test_solve_cplex_mip_optimal(monkeypatch, tmp_path):
    rec = {}
    fake_cplex(monkeypatch, "Welcome to IBM(R) ILOG(R) CPLEX(R) Interactive Optimizer 22.2.0.0\n"
                            "MIP - Integer optimal solution:  Objective =  5.5000000000e+01\n", opt55_values(), rec)
    inst = read_instance(FT06)
    r = cm.solve_cplex_mip(inst, 47, 59, time_limit=30, threads=1, seed=7, workdir=tmp_path)
    assert r["status"] == "OPTIMAL" and r["makespan"] == 55 and r["version"] == "22.2.0.0"
    assert validate_schedule(inst, r["starts"], 55) == []
    for needle in ("set clocktype 2", "set timelimit 30.0", "set threads 1", "set randomseed 7",
                   "set mip tolerances mipgap 0", "optimize", "quit"):
        assert needle in rec["input"]
    assert rec["input"].index("read ") < rec["input"].index("optimize") < rec["input"].index("write ")


def test_solve_cplex_mip_timeout_with_incumbent_and_bound(monkeypatch, tmp_path):
    fake_cplex(monkeypatch, "MIP - Time limit exceeded, integer feasible:  Objective =  5.5e+01\n"
                            "Current MIP best bound =  5.0300000000e+01 (gap = 4.7, 8.5%)\n", opt55_values())
    r = cm.solve_cplex_mip(read_instance(FT06), 47, 59, workdir=tmp_path)
    assert r["status"] == "FEASIBLE" and r["best_bound"] == 50.3 and r["makespan"] == 55


def test_solve_cplex_mip_no_solution_file(monkeypatch, tmp_path):
    fake_cplex(monkeypatch, "MIP - Time limit exceeded, no integer solution.\n", None)
    r = cm.solve_cplex_mip(read_instance(FT06), 47, 59, workdir=tmp_path)
    assert r["status"] == "UNKNOWN" and r["starts"] is None


def test_solve_cplex_mip_not_installed(monkeypatch):
    monkeypatch.setattr(cm, "find_exe", lambda kind: None)
    assert cm.solve_cplex_mip(read_instance(FT06), 47, 59) == {"status": "NOT_INSTALLED"}


def test_solve_cplex_mip_incomplete_solution_is_not_trusted(monkeypatch, tmp_path):
    vals = opt55_values()
    del vals["s_3_3"]
    fake_cplex(monkeypatch, "MIP - Integer optimal solution:  Objective =  5.5e+01\n", vals)
    r = cm.solve_cplex_mip(read_instance(FT06), 47, 59, workdir=tmp_path)
    assert r["starts"] is None and r["status"] == "OPTIMAL"          # khung ben ngoai se xem day la ERROR, khong tin


# ------------------------------------------------------------------ docplex GIA (kiem tra phan keo day, khong giai that)
class FakeExpr:
    def __le__(self, other):
        return ("le", other)


def install_fake_docplex(monkeypatch, status="Optimal", has=True, bound=55.0, seen=None):
    names = {}

    class Model:
        def interval_var(self, start=None, size=None, name=None):
            names[name] = (start, size)
            return name

        def end_before_start(self, a, b):
            return ("ebs", a, b)

        def no_overlap(self, ivs):
            return ("no_overlap", tuple(ivs))

        def integer_var(self, lo, hi, name):
            return ("int", lo, hi)

        def end_of(self, v):
            return FakeExpr()

        def add(self, c):
            seen.setdefault("cons", []).append(c)

        def minimize(self, e):
            return ("min", e)

        def solve(self, **kw):
            seen["kw"] = kw
            return Res()

    class Res:
        def is_solution(self):
            return has

        def get_solve_status(self):
            return status

        def get_var_solution(self, v):
            l, i = map(int, v.split("_")[1:])
            return SimpleNamespace(get_start=lambda: OPT55[l][i])

        def get_objective_values(self):
            return (55,)

        def get_objective_bounds(self):
            return (bound,)

    mod_cp = types.ModuleType("docplex.cp")
    mod_model = types.ModuleType("docplex.cp.model")
    mod_model.CpoModel = Model
    mod = types.ModuleType("docplex")
    mod.__version__ = "9.9.9"
    mod.cp = mod_cp
    mod_cp.model = mod_model
    monkeypatch.setitem(sys.modules, "docplex", mod)
    monkeypatch.setitem(sys.modules, "docplex.cp", mod_cp)
    monkeypatch.setitem(sys.modules, "docplex.cp.model", mod_model)
    return names


def test_solve_cpo_glue_with_fake_docplex(monkeypatch):
    import jssp.cpo as cpo
    seen = {}
    names = install_fake_docplex(monkeypatch, seen=seen)
    monkeypatch.setattr(cpo, "find_exe", lambda kind: "C:/fake/cpoptimizer.exe")
    inst = read_instance(FT06)
    r = cpo.solve_cpo(inst, 47, 59, time_limit=12, workers=1, seed=3)
    assert r["status"] == "OPTIMAL" and r["makespan"] == 55 and r["best_bound"] == 55.0 and r["version"] == "9.9.9"
    assert validate_schedule(inst, r["starts"], 55) == []
    assert seen["kw"]["TimeLimit"] == 12.0 and seen["kw"]["Workers"] == 1 and seen["kw"]["RandomSeed"] == 3
    assert seen["kw"]["execfile"] == "C:/fake/cpoptimizer.exe"
    # cua so bat dau dung head/tail: thao tac dau cua job 0 (do dai 1; cac thao tac sau dai 3+6+7+3+6=25): start trong [0, 59-25-1]
    assert names["iv_0_0"] == ((0, 59 - 25 - 1), 1)
    kinds = [c[0] for c in seen["cons"] if isinstance(c, tuple)]
    assert kinds.count("no_overlap") == 6 and kinds.count("ebs") == 6 * 5      # 6 may, 5 rang buoc thu tu moi job


def test_solve_cpo_unknown_without_solution(monkeypatch):
    import jssp.cpo as cpo
    install_fake_docplex(monkeypatch, status="Unknown", has=False, bound=48.0, seen={})
    r = cpo.solve_cpo(read_instance(FT06), 47, 59)
    assert r["status"] == "UNKNOWN" and r["starts"] is None and r["makespan"] is None and r["best_bound"] == 48.0


def test_map_cpo_status():
    assert map_cpo_status("Optimal", True) == "OPTIMAL"
    assert map_cpo_status("Feasible", True) == "FEASIBLE"
    assert map_cpo_status("Infeasible", False) == "INFEASIBLE"
    assert map_cpo_status("Unknown", False) == "UNKNOWN"
    assert map_cpo_status("Unknown", True) == "FEASIBLE"


# ------------------------------------------------------------------ khung chay (child gia)
@pytest.mark.parametrize("fn,method,solver", [(bl.run_cpo, "cpo", "cpo-w1"), (bl.run_cplex, "cplex", "cplex-t1")])
def test_optimal_is_logged_and_saved(monkeypatch, tmp_path, fn, method, solver):
    fake_child(monkeypatch, {"status": "OPTIMAL", "makespan": 55, "best_bound": 55.00002, "starts": OPT55})
    log = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    r = fn(FT06, time_limit=10, summary_log=log, save_dir=tmp_path / "sch", verbose=False)
    assert r.optimal and r.lb == r.ub == 55 and r.method == method and r.solver == solver
    row = list(csv.DictReader(open(tmp_path / "s.csv", encoding="utf-8")))[0]
    assert row["method"] == method and row["solver"] == solver and row["lb_init"] == "47"
    assert (tmp_path / "sch" / f"ft06_{method}_{solver}.json").exists()


@pytest.mark.parametrize("fn", [bl.run_cpo, bl.run_cplex])
def test_bound_noise_and_never_above_schedule(monkeypatch, fn):
    fake_child(monkeypatch, {"status": "FEASIBLE", "makespan": 55, "best_bound": 50.00004, "starts": OPT55})
    r = fn(FT06, verbose=False)
    assert (r.lb, r.ub, r.status) == (50, 55, "TIMEOUT")
    fake_child(monkeypatch, {"status": "FEASIBLE", "makespan": 55, "best_bound": 99.0, "starts": OPT55})
    r = fn(FT06, verbose=False)
    assert r.lb <= r.ub == 55


@pytest.mark.parametrize("fn,method", [(bl.run_cpo, "cpo"), (bl.run_cplex, "cplex")])
@pytest.mark.parametrize("st", ["NOT_INSTALLED", "LICENSE_LIMIT"])
def test_license_problems_write_nothing_and_say_why(monkeypatch, tmp_path, capsys, fn, method, st):
    fake_child(monkeypatch, {"status": st, "message": "x"})
    log = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    r = fn(FT06, summary_log=log, save_dir=tmp_path / "sch")
    assert r.status == st and not r.optimal
    assert not (tmp_path / "s.csv").exists() and not (tmp_path / "sch").exists()
    out = capsys.readouterr().out
    assert st in out and ("Studio" in out or "docplex" in out)


def test_invalid_cplex_schedule_is_rejected(monkeypatch):
    fake_child(monkeypatch, {"status": "OPTIMAL", "makespan": 55, "best_bound": 55.0, "starts": [[0] * 6 for _ in range(6)]})
    assert bl.run_cplex(FT06, verbose=False).status == "ERROR"
    fake_child(monkeypatch, {"status": "OPTIMAL", "makespan": 55, "best_bound": 55.0, "starts": None})
    assert bl.run_cplex(FT06, verbose=False).status == "ERROR"      # cplex.exe bao toi uu nhung khong doc duoc nghiem


def test_solver_labels_and_suite_defaults():
    assert solver_label("cpo", "cadical153", False, 1) == "cpo-w1"
    assert solver_label("cplex", "cadical153", True, 4) == "cplex-t4"
    from jssp.suite import ALL_METHODS, TIERS
    assert "cpo" in ALL_METHODS and "cplex" in ALL_METHODS
    assert "cpo" in TIERS["medium"][2] and "cplex" in TIERS["large"][2]


def test_suite_marks_cplex_dead_independently_of_other_methods(tmp_path):
    cells = [Cell(FT06, n, "6x6", m, m, True, "x") for n in ("a", "b") for m in ("cplex", "cpo")]
    calls = []

    def fake_cx(path, *a):
        calls.append("cplex")
        return SimpleNamespace(method="cplex", status="NOT_INSTALLED")

    def fake_cpo(path, *a):
        calls.append("cpo")
        return SimpleNamespace(method="cpo", status="TIMEOUT")

    results, _ = run_suite(cells, 60, out_dir=tmp_path / "raw", run_cx=fake_cx, run_cpo=fake_cpo, say=lambda s: None)
    assert calls == ["cplex", "cpo", "cpo"] and [r.method for r in results] == ["cpo", "cpo"]


# ------------------------------------------------------------------ studio.find_exe
def test_find_exe_override_and_missing(monkeypatch, tmp_path):
    fake = tmp_path / "cplex.exe"
    fake.write_text("x")
    monkeypatch.setenv("JSSP_CPLEX_EXE", str(fake))
    assert studio.find_exe("cplex") == str(fake)
    monkeypatch.delenv("JSSP_CPLEX_EXE")
    monkeypatch.setattr(studio, "studio_dirs", lambda: [])
    monkeypatch.setattr(studio.shutil, "which", lambda name: None)
    assert studio.find_exe("cplex") is None and studio.find_exe("cpoptimizer") is None


def test_find_exe_in_studio_dir(monkeypatch, tmp_path):
    exe = tmp_path / "CPLEX_Studio222" / "cplex" / "bin" / "x64_win64" / "cplex.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("x")
    monkeypatch.delenv("JSSP_CPLEX_EXE", raising=False)
    monkeypatch.setattr(studio, "studio_dirs", lambda: [str(tmp_path / "CPLEX_Studio222")])
    assert studio.find_exe("cplex") == str(exe)


# ------------------------------------------------------------------ script con
def test_run_cpo_script_reports_missing_package():
    code = ("import sys, runpy; sys.modules['docplex'] = None; "
            f"sys.argv = ['run_cpo.py', r'{FT06}']; runpy.run_path(r'{ROOT / 'scripts' / 'run_cpo.py'}', run_name='__main__')")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert json.loads(r.stdout.strip().splitlines()[-1]) == {"status": "NOT_INSTALLED"}


def test_run_cplex_script_reports_missing_exe(monkeypatch, capsys):
    monkeypatch.setattr(cm, "find_exe", lambda kind: None)
    spec = importlib.util.spec_from_file_location("run_cplex_script", ROOT / "scripts" / "run_cplex.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(sys, "argv", ["run_cplex.py", str(FT06)])
    assert mod.main() == 0
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == "NOT_INSTALLED"


# ------------------------------------------------------------------ giai that (can Studio / docplex that)
def real_cplex_or_skip():
    if not studio.find_exe("cplex"):
        pytest.skip("khong thay cplex.exe")
    r = cm.solve_cplex_mip(read_instance(FT06), 47, 59, time_limit=60)
    if r["status"] in ("NOT_INSTALLED", "LICENSE_LIMIT"):
        pytest.skip(f"cplex.exe khong dung duoc: {r['status']}")


def real_cpo_or_skip():
    pytest.importorskip("docplex.cp.model")
    if not studio.find_exe("cpoptimizer"):
        pytest.skip("khong thay cpoptimizer.exe")


def test_real_cplex_mip_ft06():
    real_cplex_or_skip()
    inst = read_instance(FT06)
    r = cm.solve_cplex_mip(inst, 47, 59, time_limit=120)
    assert r["status"] == "OPTIMAL" and r["makespan"] == 55
    assert validate_schedule(inst, r["starts"], 55) == []


def test_real_cplex_mip_matches_brute_force_on_random_tiny():
    real_cplex_or_skip()
    rng = random.Random(3)
    for _ in range(6):
        inst = random_tiny(rng)
        ub = makespan(inst, best_greedy(inst))
        r = cm.solve_cplex_mip(inst, inst.trivial_lower_bound(), ub, time_limit=30)
        assert r["status"] == "OPTIMAL" and r["makespan"] == brute_force_optimum(inst)
        assert validate_schedule(inst, r["starts"], ub) == []


def test_real_cplex_mip_time_limit_gives_bound():
    real_cplex_or_skip()
    try:
        inst = read_instance(resolve_instance("ft10"))              # ft10 nam trong data/instances (fetch_benchmarks.py)
    except FileNotFoundError:
        pytest.skip("chua co data/instances/ft10.txt")
    r = cm.solve_cplex_mip(inst, inst.trivial_lower_bound(), 1074, time_limit=3)
    assert r["status"] in ("FEASIBLE", "UNKNOWN", "OPTIMAL")
    assert r["best_bound"] is not None                               # doc duoc can duoi tu nhat ky that


def test_real_cpo_ft06():
    real_cpo_or_skip()
    from jssp.cpo import solve_cpo
    inst = read_instance(FT06)
    r = solve_cpo(inst, 47, 59, time_limit=60)
    assert r["status"] == "OPTIMAL" and r["makespan"] == 55
    assert validate_schedule(inst, r["starts"], 55) == []


def test_real_cpo_matches_brute_force_on_random_tiny():
    real_cpo_or_skip()
    from jssp.cpo import solve_cpo
    rng = random.Random(3)
    for _ in range(6):
        inst = random_tiny(rng)
        ub = makespan(inst, best_greedy(inst))
        r = solve_cpo(inst, inst.trivial_lower_bound(), ub, time_limit=30)
        assert r["status"] == "OPTIMAL" and r["makespan"] == brute_force_optimum(inst)
        assert validate_schedule(inst, r["starts"], ub) == []


@pytest.mark.parametrize("which", ["cplex", "cpo"])
def test_real_end_to_end_subprocess(tmp_path, which):
    (real_cplex_or_skip if which == "cplex" else real_cpo_or_skip)()
    fn = bl.run_cplex if which == "cplex" else bl.run_cpo
    log = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    r = fn(FT06, time_limit=120, summary_log=log, verbose=False)
    assert r.optimal and r.lb == r.ub == 55
    assert list(csv.DictReader(open(tmp_path / "s.csv", encoding="utf-8")))[0]["method"] == which
