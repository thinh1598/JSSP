# Ngày 3 – Mã hóa Crawford, giải mã lịch, kiểm tra lịch

## File mới (chép vào repo, giữ nguyên đường dẫn)
- `src/jssp/crawford.py`  : bộ mã hóa 8 quy tắc (+ R9), giải mã lịch, in clause dễ đọc
- `src/jssp/validate.py`  : kiểm tra lịch hợp lệ (độc lập với SAT)
- `src/jssp/sat_solve.py` : giải S_L bằng PySAT, giải mã, kiểm tra
- `src/jssp/gantt.py`     : vẽ Gantt để nhìn bằng mắt
- `src/jssp/minisolver.py`: solver DPLL nhỏ, chỉ để test khi chưa có PySAT
- `scripts/show_example.py`, `scripts/run_sat.py`
- `tests/test_crawford.py`, `notes/crawford_notes.md`

## Chạy (trong thư mục có README.md, đã kích hoạt .venv)
```powershell
pytest                                   # mong đợi: 18 passed, 1 skipped
python scripts/show_example.py 8         # xem toàn bộ clause của bài tay 2x2, đối chiếu với bài tập giấy
python scripts/show_example.py 7         # xem "bậc thang" sa và lịch giải mã
python scripts/run_sat.py data/ft06.txt --L 55 --gantt results/figures/ft06_55.png
python scripts/run_sat.py data/ft06.txt --L 54
```
- L = 55 phải ra SAT, "kiểm tra hợp lệ: OK".
- L = 54 phải ra UNSAT (cùng với L = 55 SAT => tối ưu FT06 = 55). Nếu quá vài phút thì Ctrl+C, báo lại.
- Nếu L = 55 ra UNSAT, hoặc báo "KHONG hop le": có lỗi mã hóa, dán nguyên văn kết quả cho mình.

## Commit
```powershell
git add .
git commit -m "Day 3: Crawford encoder, validator, solver wrapper, tests"
git push
```
