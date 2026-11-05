# Tổng quan dự án (đọc file này khi quên)

## Dự án làm gì (một câu)

Cho một bài xếp lịch JSSP, tìm **makespan nhỏ nhất** bằng cách hỏi SAT solver nhiều lần:
"có lịch với makespan ≤ L không?" (SAT = có, UNSAT = không).
Tối ưu = k khi hỏi L = k−1 ra UNSAT và hỏi L = k ra SAT.

## Sáu ngày = sáu lớp xếp chồng

| Ngày | Có thêm gì | Một câu |
|---|---|---|
| 1 | Môi trường, repo | Máy chạy được Python + PySAT |
| 2 | Đọc đề, 81 bài benchmark | Chương trình hiểu bài toán |
| 3 | Mã hóa Crawford + giải SAT | Trả lời "có lịch ≤ L không?" **một lần** |
| 4 | Kiểm tra với đáp án đã biết | Biết chương trình đúng |
| 5 | Tìm tối ưu tự động + ghi CSV | Hỏi nhiều lần để ra đáp án |
| 6 | Incremental SAT | Mã hóa 1 lần, đổi L bằng assumptions, solver giữ lại thứ đã học |

## Bản đồ file (trong `src/jssp/`)

| File | Vai trò | Quan trọng cho báo cáo? |
|---|---|---|
| `instance.py` | Đọc file đề → đối tượng `inst` | Hiểu sơ |
| `crawford.py` | **Mã hóa bài toán thành SAT (luật R1–R9)** | **Có, trái tim của bài** |
| `sat_solve.py` | Nhận `inst` + L → mã hóa → PySAT giải → kiểm tra lịch | Hiểu sơ |
| `validate.py` | Kiểm tra một lịch có hợp lệ không | Hiểu sơ |
| `heuristic.py` | Lịch tạm bằng luật đơn giản → cận trên ban đầu | Không |
| `runner.py` | Chạy lệnh trong tiến trình riêng, giới hạn giờ/RAM, ghi CSV | Không (chỉ cần biết có) |
| `search_multi.py` | **Bộ não: hai cách chọn L (giảm dần / chia đôi), mỗi cách có bản thường và bản incremental** | **Có** |
| `incremental.py` | Ngày 6: phiên solver sống lâu, đổi L bằng assumptions | **Có** |
| `gantt.py` | Vẽ biểu đồ Gantt | Dùng cho hình |
| `minisolver.py` | DPLL nhỏ, chỉ để test khi không có PySAT | Không |

## Luồng một lần chạy tìm tối ưu

```
search_opt.py  →  search_multi.search()
                    ├─ heuristic.py ............ cận trên ban đầu (hi), gọi 1 lần
                    └─ lặp: chọn L → runner.py chạy run_sat.py --L L --json
                                        └─ sat_solve.py → crawford.py + PySAT
                         đọc kết quả → cập nhật lo/hi → ghi 1 dòng vào calls.csv
```

`lo` = cận dưới đã chứng minh (có lần UNSAT). `hi` = makespan của lịch đã có thật.
Dừng khi `lo == hi`.

## Lệnh hay dùng (chạy trong thư mục chứa `scripts/`, đã bật `.venv`)

| Mục đích | Lệnh |
|---|---|
| Kiểm tra môi trường | `python scripts/check_env.py` |
| Xem thông tin một bài | `python -m jssp.info data/ft06.txt` (hoặc script `info` tương ứng) |
| Giải một lần với L | `python scripts/run_sat.py data/ft06.txt --L 55` |
| Kiểm tra với đáp án đã biết | `python scripts/verify_known.py` |
| Tìm tối ưu (cả 2 cách) | `python scripts/search_opt.py ft06 --method both` |
| Incremental SAT | `python scripts/search_opt.py ft06 --method inc_both` |
| So cả 4 cách | `python scripts/search_opt.py ft06 la01 --method all` |
| Chạy test | `python -m pytest` |

## Kết quả hiện có

| Bài | Tối ưu |
|---|---|
| FT06 | 55 |
| la01 | 666 |
| la02 | 655 |
| la03 | 597 |
| la04 | 590 |
| la05 | 593 |
| FT10 | 930 |

- Chia đôi nhanh hơn giảm dần rõ rệt: FT10 cần **8 lần giải / 70 giây** (chia đôi) so với **128 lần / 436 giây** (giảm dần).
- Phần khó tập trung gần giá trị tối ưu; cận dưới (LB) trong cách giảm dần đứng yên đến cuối.
- RAM FT10 khoảng 360–407 MB; sinh CNF khoảng 0,5 giây.
- Số liệu thô: `results/raw/calls.csv` (mỗi lần giải một dòng), `results/raw/summary.csv` (mỗi lần tìm một dòng).

## Còn lại phải làm (theo kế hoạch)

1. Chạy Incremental SAT trên máy bạn và so với cách cũ (ngày 6).
2. Baseline: CP-SAT, CPLEX CP/MIP, Gurobi (thư mục `models/`).
3. Thêm solver SAT (Glucose, CryptoMiniSat/Kissat).
4. Bài lớn hơn (ABZ, YN, TA).
5. Cải tiến/ablation, vẽ hình (cnsplots), báo cáo LaTeX `cas-sc`, dọn README.

## Việc cần nhớ

- Chạy `python -m pytest` và xác nhận tất cả test qua (kỳ vọng sau ngày 6: 37 passed, 1 skipped).
- Chạy `python scripts/verify_known.py` **một lần cho tất cả bài** (mỗi lần chạy ghi đè `small_check.md`).
- Các cận "literature" trong `data/known_bounds.csv` cần đối chiếu nguồn công khai trước khi trích dẫn.
