# Ngày 5 (T7) – Tự tìm tối ưu: "SAT nhiều lần" + khung chạy thực nghiệm

## Ý tưởng (một đoạn)
Trước giờ bạn tự chọn L rồi hỏi solver "có lịch xong trong L không?". Giờ chương trình tự hỏi nhiều lần để tìm L nhỏ nhất:
- **giảm dần (descent)**: bắt đầu từ một lịch có sẵn (makespan = UB). Hỏi L = UB-1. Có lịch -> hạ UB xuống makespan mới, hỏi tiếp. Không có -> UB chính là tối ưu.
- **chia đôi (binary)**: giữ khoảng [LB, UB]. Hỏi L ở giữa. Có lịch -> UB = makespan tìm được. Không có -> LB = L+1. Dừng khi LB = UB.
Mỗi lần hỏi là một lần giải độc lập (sinh CNF mới, chạy trong một tiến trình riêng, có giới hạn thời gian/RAM).
"Nhiều lần" nghĩa là vậy (Incremental SAT, giữ lại solver giữa các lần hỏi, là bước sau).

## File mới (chép vào repo, giữ nguyên đường dẫn; run_sat.py thay bản cũ)
- `src/jssp/heuristic.py`     : xếp lịch nhanh, lấy UB ban đầu (luôn là lịch hợp lệ có thật)
- `src/jssp/runner.py`        : chạy một lệnh trong tiến trình riêng, giới hạn thời gian/RAM, đo RAM đỉnh, ghi CSV
- `src/jssp/search_multi.py`  : hai cách tìm tối ưu ở trên
- `scripts/search_opt.py`     : lệnh để chạy (bạn chỉ cần dùng file này)
- `scripts/run_sat.py`        : (thay bản cũ) thêm lịch vào dòng JSON
- `tests/test_search.py`

## Chạy (trong thư mục có README.md, đã kích hoạt .venv)
```powershell
pytest                                                    # mong đợi: 25 passed, 1 skipped
python scripts/search_opt.py ft06 --method both           # vài giây; cả hai cách phải ra "toi uu 55"
python scripts/search_opt.py la01 la02 --method both
python scripts/search_opt.py ft10 --method both --total-timeout 3600
```
Với bài lớn (ví dụ ABZ9) nên đặt giới hạn: `--per-call-timeout 3600 --total-timeout 86400 --mem-limit-mb 8000`.
Nếu có cận từ tài liệu: `--lb 662 --ub 678` (UB được xác nhận bằng một lần giải; LB thì được tin, không kiểm chứng).

## Kết quả ghi ở đâu (đừng mở file CSV bằng Excel khi đang chạy, Windows sẽ khóa file)
- `results/raw/calls.csv`   : mỗi lần giải một dòng: L, SAT/UNSAT/TIMEOUT/MEMOUT, makespan, số biến, số clause, thời gian, RAM đỉnh (MB), LB/UB sau lần đó
- `results/raw/summary.csv` : mỗi lần tìm một dòng: LB/UB đầu và cuối, có tối ưu không, số lần giải, tổng thời gian
- `results/schedules/*.json`: lịch tốt nhất tìm được (dùng để vẽ Gantt sau)

## Đọc kết quả
| Trạng thái | Nghĩa |
|---|---|
| OPTIMAL (LB = UB) | đã chứng minh tối ưu |
| TIMEOUT / MEMOUT | dừng giữa chừng; [LB, UB] vẫn là khoảng ĐÃ CHỨNG MINH (giống Bảng 5 của bài báo) |
| UB_INVALID | UB bạn đưa vào bằng --ub quá nhỏ (không có lịch) |
| ERROR | lỗi; xem cột detail trong calls.csv, dán cho mình |

## Lưu ý
- Sinh CNF bằng Python mất thời gian khi L lớn (hàng triệu clause); với FT10, những lần hỏi L lớn có thể mất vài chục giây chỉ để sinh CNF.
- Mình chưa chạy các lệnh này với PySAT thật (môi trường của mình không cài được); test ở đây dùng solver nhỏ. Thời gian thật trên FT10 bạn cho mình biết.

## Commit
```powershell
git add .
git commit -m "T7: multi-call SAT search (descent, binary) + runner with timeout/RAM/CSV"
git push
```
