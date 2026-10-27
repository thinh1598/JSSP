"""In ra TOAN BO clause cua bai tay 2 job x 2 may (DAY1_GUIDE muc D), nhom theo quy tac.

Chay:  python scripts/show_example.py          (L = 8)
       python scripts/show_example.py 7        (L = 7: vua du; thu 6 de thay UNSAT)
Muc dich: nhin tan mat code sinh clause ra cai gi, va doc 'bac thang' sa[...] cua nghiem.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.crawford import CrawfordEncoder  # noqa: E402
from jssp.instance import JSSPInstance  # noqa: E402
from jssp.minisolver import solve_dpll  # noqa: E402

L = int(sys.argv[1]) if len(sys.argv) > 1 else 8
# Job A: (M1,3) -> (M2,2).  Job B: (M2,2) -> (M1,4).   May danh so tu 0 nen M1 = 0, M2 = 1.
inst = JSSPInstance("hand", 2, 2, [[(0, 3), (1, 2)], [(1, 2), (0, 4)]])
enc = CrawfordEncoder(inst, L)
if enc.trivially_unsat:
    sys.exit(f"L = {L} qua nho: co job dai hon L => khong co lich (UNSAT ngay, khong can sinh CNF)")

DESC = {
    "R1": "thu tu trong job",
    "R2": "hai thao tac cung may khong chong nhau",
    "R3": "can duoi thoi diem bat dau (don vi)",
    "R4": "can tren thoi diem ket thuc (don vi)",
    "R5": "sa don dieu: sa[t] -> sa[t-1]",
    "R6": "eb don dieu: eb[t] -> eb[t+1]",
    "R7": "do dai thao tac: sa[t] -> NOT eb[t+p-1]",
    "R8": "gan thu tu voi thoi gian: sa[a,t] ^ pr[a,b] -> sa[b,t+p_a]",
    "R9": "(bo sung) khong the bat dau qua muon: NOT sa[t], t > L-p",
}
s = enc.stats()
print(f"Bai: A=(M1,3),(M2,2)  B=(M2,2),(M1,4)   L = {L}")
print(f"Tong: {s['vars']} bien, {s['clauses']} clause\n")
for rule in ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"]:
    a, b = enc.rule_ranges[rule]
    print(f"== {rule}: {DESC[rule]}   ({b - a} clause)")
    shown = enc.clauses[a:b]
    for c in shown[:8]:
        print("   ", enc.format_clause(c))
    if len(shown) > 8:
        print(f"    ... (con {len(shown) - 8} clause cung dang)")
    print()

try:
    import pysat  # noqa: F401
    from jssp.sat_solve import pysat_backend
    backend, who = pysat_backend("cadical153"), "PySAT/CaDiCaL"
except ImportError:
    backend, who = solve_dpll, "solver DPLL nho (chua cai PySAT)"
model = backend(enc.clauses, enc.num_vars)
print(f"Giai bang {who}: {'KHONG THOA (UNSAT)' if model is None else 'THOA (SAT)'}")
if model is not None:
    truth = {abs(x) for x in model if x > 0}
    print("\nBac thang sa[op, t>=t] voi t = 0.." + str(L) + "  (1 = dung, 0 = sai):")
    for op in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        row = "".join("1" if enc.sa(op, t) in truth else "0" for t in range(L + 1))
        start = row.rfind("1")
        print(f"  {enc.op_name(op)}: {row}   -> bat dau = vi tri '1' cuoi cung = {start}")
    print("\nLich giai ma:", enc.decode(model))
