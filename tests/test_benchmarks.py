"""Kiem tra du lieu benchmark: moi file trong data/ phai doc duoc va hop le."""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.instance import read_instance  # noqa: E402


def _all_instance_files():
    files = list((ROOT / "data").glob("*.txt")) + list((ROOT / "data" / "instances").glob("[!_]*.txt"))
    return sorted(files)


def test_every_instance_file_is_valid():
    files = _all_instance_files()
    assert files, "khong co file bai nao trong data/"
    for f in files:
        inst = read_instance(f)
        # JSSP chuan: moi job di qua moi may dung 1 lan
        for job in inst.jobs:
            assert len(job) == inst.n_machines, f
            assert sorted(m for m, _ in job) == list(range(inst.n_machines)), f
        assert inst.trivial_lower_bound() <= inst.trivial_upper_bound()


def test_known_bounds_consistent():
    with open(ROOT / "data" / "known_bounds.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    for r in rows:
        lb, ub = int(r["lb"]), int(r["ub"])
        assert lb <= ub, r
        if r["status"] == "optimal":
            assert lb == ub, r


def test_known_bounds_vs_trivial_lb():
    """Cac bai da co file: LB don gian khong duoc vuot toi uu da biet."""
    with open(ROOT / "data" / "known_bounds.csv", encoding="utf-8") as fh:
        known = {r["instance"]: int(r["lb"]) for r in csv.DictReader(fh)}
    for f in _all_instance_files():
        inst = read_instance(f)
        if inst.name in known:
            assert inst.trivial_lower_bound() <= known[inst.name], inst.name


def test_fetch_script_splits_orlib_file(tmp_path):
    src = tmp_path / "jobshop1.txt"
    src.write_text(
        " +++++\n instance tiny\n 2x2 thu\n 2 2\n 0 3 1 2\n 1 2 0 4\n"
        " +++++\n instance tiny2\n 1x2\n 1 2\n 0 5 1 5\n",
        encoding="utf-8")
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "fetch_benchmarks.py"),
                        "--from-file", str(src), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    a = read_instance(out / "tiny.txt")
    assert a.jobs == [[(0, 3), (1, 2)], [(1, 2), (0, 4)]]
    assert read_instance(out / "tiny2.txt").jobs == [[(0, 5), (1, 5)]]
