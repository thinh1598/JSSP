"""Kiem tra CPLEX (ban 2): tim Studio, thu 3 duong giai tren mo hinh NHO (30 bien) va LON (1500 bien),
va in ra dong bao loi that cua tung duong. Ban community bi gioi han ~1000 bien / 1000 rang buoc.

    python scripts/check_cplex.py

Bai thu: tap doc lap lon nhat tren duong di n dinh: n bien nhi phan, n-1 rang buoc, dap an n/2.
"""
import glob
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SMALL, BIG = 30, 1500
print("python:", sys.version.split()[0])

dirs = [v for k, v in os.environ.items() if k.upper().startswith("CPLEX_STUDIO_DIR")]
dirs += glob.glob(r"C:\Program Files\IBM\ILOG\CPLEX_Studio*") + glob.glob(r"C:\Program Files (x86)\IBM\ILOG\CPLEX_Studio*")
studio = dirs[0] if dirs else None
print("Studio:", studio or "KHONG TIM THAY")
cplex_exe = cpo_exe = None
if studio:
    c = glob.glob(os.path.join(studio, "cplex", "bin", "x64_win64", "cplex.exe"))
    cplex_exe = c[0] if c else None
    c = glob.glob(os.path.join(studio, "cpoptimizer", "bin", "x64_win64", "cpoptimizer.exe"))
    cpo_exe = c[0] if c else None
    pydirs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(studio, "cplex", "python", "*")))
    print("goi Python day du di kem Studio (cho cac ban Python):", pydirs or "khong co")
verdict = {}


def tail(text, k=12):
    return "\n".join("      | " + ln for ln in text.strip().splitlines()[-k:])


# ---------------------------------------------------------------- 1. goi Python cplex (pip)
def py_cplex(n):
    import cplex
    c = cplex.Cplex()
    for s in (c.set_log_stream, c.set_results_stream, c.set_warning_stream, c.set_error_stream):
        s(None)
    c.variables.add(obj=[1.0] * n, types=["B"] * n)
    c.objective.set_sense(c.objective.sense.maximize)
    for i in range(n - 1):
        c.linear_constraints.add(lin_expr=[cplex.SparsePair([i, i + 1], [1.0, 1.0])], senses=["L"], rhs=[1.0])
    c.solve()
    return round(c.solution.get_objective_value())


print("\n[1] goi Python cplex (cai bang pip)")
try:
    import cplex
    print("    phien ban", getattr(cplex, "__version__", "?"))
    res = []
    for n in (SMALL, BIG):
        try:
            res.append(f"{n} bien: {'DUOC' if py_cplex(n) == n // 2 else 'sai ket qua'}")
        except Exception as e:                           # noqa: BLE001
            res.append(f"{n} bien: LOI {str(e).strip().splitlines()[0][:90]}")
    verdict["python-cplex"] = " | ".join(res)
except ImportError:
    verdict["python-cplex"] = "chua cai"
print("    =>", verdict["python-cplex"])


# ---------------------------------------------------------------- 2. CP Optimizer
def cpo(n):
    from docplex.cp.model import CpoModel
    m = CpoModel()
    x = [m.integer_var(0, 1, f"x{i}") for i in range(n)]
    for i in range(n - 1):
        m.add(x[i] + x[i + 1] <= 1)                      # chi can kha thi: x = 0 la mot nghiem
    log = io.StringIO()
    kw = {"TimeLimit": 30, "log_output": log}
    if cpo_exe:
        kw["execfile"] = cpo_exe
    r = m.solve(**kw)
    return r.is_solution(), str(r.get_solve_status()), log.getvalue()


print("\n[2] CP Optimizer (docplex.cp + cpoptimizer.exe)")
try:
    import docplex.cp.model  # noqa: F401  (bao ImportError som neu chua cai)
    res, last_log = [], ""
    for n in (SMALL, BIG):
        try:
            ok, st, log = cpo(n)
            res.append(f"{n} bien: {'DUOC' if ok else 'KHONG RA NGHIEM (' + st + ')'}")
            if not ok:
                last_log = log
        except Exception as e:                           # noqa: BLE001
            res.append(f"{n} bien: LOI {str(e).strip().splitlines()[0][:90]}")
    verdict["cp-optimizer"] = " | ".join(res)
    if last_log:
        print("    nhat ky cua lan khong ra nghiem:\n" + tail(last_log))
except ImportError:
    verdict["cp-optimizer"] = "chua cai docplex"
print("    =>", verdict["cp-optimizer"])


# ---------------------------------------------------------------- 3. cplex.exe doc file .lp
def lp_text(n):
    lines = ["Maximize", " obj:"]
    for i in range(0, n, 10):
        lines.append("   " + " + ".join(f"x{j}" for j in range(i, min(n, i + 10))) + (" +" if i + 10 < n else ""))
    lines.append("Subject To")
    lines += [f" c{i}: x{i} + x{i + 1} <= 1" for i in range(n - 1)]
    lines.append("Binary")
    for i in range(0, n, 10):
        lines.append("   " + " ".join(f"x{j}" for j in range(i, min(n, i + 10))))
    lines.append("End")
    return "\n".join(lines) + "\n"


print("\n[3] cplex.exe doc file .lp")
if not cplex_exe:
    verdict["cplex.exe"] = "khong co cplex.exe"
else:
    res, last_out = [], ""
    for n in (SMALL, BIG):
        f = Path(tempfile.mkdtemp()) / "path.lp"
        f.write_text(lp_text(n))
        try:
            p = subprocess.run([cplex_exe], input=f"read {f}\noptimize\ndisplay solution objective\nquit\n",
                               capture_output=True, text=True, timeout=180)
            out = p.stdout + p.stderr
            good = "Solution value" in out and str(n // 2) in out.split("Solution value")[-1][:30]
            res.append(f"{n} bien: {'DUOC' if good else 'KHONG RA KET QUA'}")
            if not good:
                last_out = out
        except Exception as e:                           # noqa: BLE001
            res.append(f"{n} bien: LOI {str(e)[:90]}")
    verdict["cplex.exe"] = " | ".join(res)
    if last_out:
        print("    dau ra cua lan khong ra ket qua:\n" + tail(last_out, 20))
print("    =>", verdict["cplex.exe"])

print("\n" + "=" * 60 + "\nTOM TAT")
for k, v in verdict.items():
    print(f"  {k:14s} {v}")
