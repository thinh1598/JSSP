"""Kiem tra Gurobi: ten may, phien ban, va co giai duoc mo hinh lon hon 2000 bien/rang buoc khong
(giay phep gioi han cua pip chi cho toi da 2000 bien va 2000 rang buoc tuyen tinh).

    python scripts/check_gurobi.py
"""
import socket
import sys

print("Ten may nay:", socket.gethostname(), "(so voi o 'installed on' trong Gurobi User Portal)")
try:
    import gurobipy as gp
    from gurobipy import GRB
except ImportError:
    print("Chua cai gurobipy. Chay:  pip install gurobipy")
    sys.exit(1)

print("gurobipy:", ".".join(str(v) for v in gp.gurobi.version()))

n = 3000                                     # 3000 bien, 2999 rang buoc: vuot gioi han 2000 cua giay phep gioi han
try:
    m = gp.Model("kiemtra")
    m.Params.OutputFlag = 0
    x = m.addVars(n, vtype=GRB.BINARY)
    m.addConstrs((x[i] + x[i + 1] <= 1 for i in range(n - 1)))
    m.setObjective(x.sum(), GRB.MAXIMIZE)    # tap doc lap lon nhat tren duong di 3000 dinh = 1500
    m.optimize()
except gp.GurobiError as e:
    print("LOI Gurobi:", e)
    if "size-limited" in str(e).lower() or "too large" in str(e).lower():
        print("=> Dang dung giay phep GIOI HAN KICH THUOC. Chua co giay phep day du tren may nay.")
    else:
        print("=> Khong tim thay / khong hop le giay phep (kiem tra file gurobi.lic va ten may).")
    sys.exit(2)

ok = m.Status == GRB.OPTIMAL and round(m.ObjVal) == n // 2
print("Ket qua:", "OK, giay phep day du, giai dung (1500)" if ok else f"bat thuong: status={m.Status}, obj={m.ObjVal}")
sys.exit(0 if ok else 3)
