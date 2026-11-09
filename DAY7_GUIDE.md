# Ngày 7 (T9): Baseline CP-SAT (OR-Tools)

## CP-SAT là gì, để làm gì

Cho tới giờ ta giải JSSP theo hướng **SAT**: chuyển bài toán thành hàng triệu mệnh đề đúng/sai, rồi nhờ SAT solver (CaDiCaL).

**CP-SAT** là một công cụ khác của Google, làm việc **trực tiếp với bài toán xếp lịch**: mỗi thao tác có một "khoảng thời gian" (bắt đầu, độ dài), và chỉ cần nói luật:
- trong một job, việc sau bắt đầu sau khi việc trước xong;
- trên một máy, các khoảng thời gian không chồng nhau (`NoOverlap`).

Đề yêu cầu so sánh hướng SAT với các công cụ khác (CP-SAT, CPLEX, Gurobi). CP-SAT là **baseline dễ nhất** để bắt đầu, vì chỉ cần `pip install`.

Ví dụ đời thường: SAT giống như bạn **dịch bài toán sang một ngôn ngữ khác** rồi nhờ người chuyên ngôn ngữ đó giải. CP-SAT giống như nhờ **chuyên gia xếp lịch** giải thẳng, không cần dịch.

## Cách so sánh công bằng (đã cài sẵn)

| Điều kiện | SAT (của mình) | CP-SAT |
|---|---|---|
| Cận dưới ban đầu | cận đơn giản | **giống hệt** |
| Cận trên ban đầu | lịch heuristic | **giống hệt** (makespan không vượt cận trên) |
| Số luồng | 1 (CaDiCaL đơn luồng) | **1 luồng mặc định** |
| Giới hạn giờ, RAM | có | có, cùng cơ chế tiến trình riêng |
| Kết quả ghi vào | `results/raw/summary.csv` | **cùng file đó**, cột `method = cpsat` |

Mặc định chỉ dùng 1 luồng vì CP-SAT bình thường chạy nhiều luồng (mỗi luồng một chiến thuật), nên so với CaDiCaL đơn luồng sẽ không công bằng. Chạy nhiều luồng nên làm thành **một thí nghiệm riêng** (`--workers 8`), ghi rõ trong báo cáo.

## Các file mới

| File | Việc |
|---|---|
| `src/jssp/cpsat.py` | Xây mô hình CP-SAT và giải |
| `scripts/run_cpsat.py` | Giải một bài, in một dòng JSON (do script dưới gọi) |
| `src/jssp/baselines.py` | Khung chạy: tiến trình riêng, giới hạn giờ/RAM, kiểm lại lịch, ghi CSV |
| `scripts/run_baseline.py` | Lệnh bạn gõ |
| `tests/test_cpsat.py` | 13 test |
| `PROJECT_OVERVIEW.md` | Cập nhật |

Các file cũ **không bị sửa**, chỉ thêm file mới.

## Cách đưa vào dự án

1. Giải nén `day7-update.zip`, chép đè vào dự án (đúng thư mục `src/`, `scripts/`, `tests/`).
2. Mở terminal ở thư mục chứa `scripts/`, bật `.venv`.
3. Cài thư viện: `pip install ortools`

## 3 lệnh chạy

**Lệnh 1: test.**
```
python -m pytest -q
```
Mong đợi: **50 passed, 1 skipped** (nếu `ortools` chưa cài thì sẽ có thêm 3 test bị bỏ qua, không sao).

**Lệnh 2: chạy thử bài nhỏ.**
```
python scripts/run_baseline.py ft06
```
Phải ra `toi uu 55`.

**Lệnh 3: các bài đã làm với SAT.**
```
python scripts/run_baseline.py la01 la02 la03 la04 ft10 --time-limit 600
```
Phải ra đúng đáp án đã biết: 666, 655, 597, 590, 930. Nếu bài nào hết giờ mà chưa chứng minh tối ưu, nó sẽ báo `TIMEOUT` kèm khoảng [LB, UB].

## Đọc kết quả

Mở `results/raw/summary.csv`, lọc cột `method = cpsat`, rồi so với `binary` / `inc_binary` ở cột `total_time`. Cột `solver` ghi `cpsat-w1` (1 luồng).

## Lưu ý trung thực

- Mình **chưa chạy được OR-Tools thật** trên máy mình (mạng bị chặn). Mình đã kiểm tra: (1) logic khung chạy bằng tiến trình giả (đúng/sai trạng thái, lịch sai bị từ chối, ghi CSV), (2) mô hình có đúng số biến, khoảng thời gian và ràng buộc mong đợi, bằng bản OR-Tools giả. Phần **giải thật** chỉ kiểm được trên máy bạn, qua 3 test cuối của `test_cpsat.py`.
- Nếu `run_baseline.py` báo `ERROR`, chạy trực tiếp `python scripts/run_cpsat.py data/ft06.txt --time-limit 30` để xem thông báo lỗi gốc, rồi gửi mình.
- Mình **không đoán trước** ai nhanh hơn. CP-SAT là công cụ rất mạnh với bài xếp lịch, có thể nhanh hơn SAT. Dù kết quả thế nào cũng là một phát hiện hợp lệ cho báo cáo.
