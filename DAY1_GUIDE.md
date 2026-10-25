# Ngày 1 – Hướng dẫn thực hiện (làm một mình)

## A. Tạo repo GitHub (5 phút)
1. Vào github.com -> New repository -> tên `jssp-sat`, chọn **Public**, KHÔNG tick "Add README".
2. Trên máy bạn, giải nén thư mục `jssp-sat`, mở terminal trong thư mục đó:
   ```bash
   git init
   git add .
   git commit -m "Day 1: project skeleton"
   git branch -M main
   git remote add origin https://github.com/<ten-ban>/jssp-sat.git
   git push -u origin main
   ```
3. Ghi link repo vào README (sau này dùng cho mục Data Availability).

## B. Cài môi trường (10 phút)
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install python-sat ortools numpy pandas matplotlib psutil pytest
python scripts/check_env.py
```
Kết quả mong đợi: dòng [ok] cho pysat, ortools, 4 solver (cadical153, glucose4, minisat22, maplechrono) và CP-SAT.
CPLEX / Gurobi hiện `[FAIL]` là bình thường; cài ở tuần 2 (`pip install docplex cplex gurobipy`).
Lưu ý: nếu `cadical153` báo lỗi, chạy `pip install -U python-sat`.

## C. Đọc lại bài báo (1–2 giờ)
Đọc `notes/paper_notes.md`, rồi đối chiếu từng quy tắc với PDF bài báo (mục 2). Tự trả lời 3 câu:
1. Vì sao dùng "bắt đầu >= t" thay vì "bắt đầu = t"?
2. Quy tắc nào đảm bảo máy chỉ làm 1 việc một lúc? (2 + 8)
3. Vì sao S_L UNSAT lại khó giải hơn S_{L+1} SAT?

## D. Bài tập nhỏ để chuẩn bị ngày 2
Tay không (giấy): job A: (M1,3),(M2,2); job B: (M2,2),(M1,4); L = 8.
Liệt kê biến pr, sa, eb và viết ra các clause quy tắc 1–3. Ngày 2 sẽ viết parser và test với FT06.

## E. Checklist
- [ ] Repo GitHub có link
- [ ] check_env.py chạy [ok]
- [ ] Đọc xong paper_notes + trả lời 3 câu
- [ ] Làm bài tập giấy mục D
