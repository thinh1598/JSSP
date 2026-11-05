# Ngày 6 (T8): Incremental SAT

## Ý tưởng một đoạn

Cách cũ ("SAT nhiều lần"): mỗi L sinh **một cnf mới** và gọi **một solver mới**, nên mọi thứ solver học được ở lần trước bị bỏ đi.

Incremental SAT: sinh cnf **một lần duy nhất** ở chân trời H (= cận trên `hi`), giữ **cùng một solver sống suốt phiên**.
Mỗi lần hỏi "có lịch ≤ L không?" ta chỉ "gài" thêm vài literal gọi là **assumptions** (chính là luật R4 với L mới).
Vì cnf gốc không đổi, các clause solver đã học được ở lần trước vẫn dùng được cho lần sau.

Ví dụ đời thường: thay vì mỗi lần hỏi lại một người mới từ đầu, bạn hỏi **cùng một người** và người đó nhớ những gì đã suy luận.

Cái giá phải trả: cnf ở H lớn hơn cnf ở L nhỏ (nhiều biến và clause hơn). **Chưa biết** bên nào nhanh hơn, đó chính là thí nghiệm của ngày này.

## Các file mới / đổi

| File | Việc | Ghi chú |
|---|---|---|
| `src/jssp/incremental.py` | **Mới**: phiên incremental + vòng tìm tối ưu | Trái tim của ngày 6 |
| `scripts/run_inc.py` | **Mới**: chạy cả phiên trong một tiến trình con, in mỗi lần hỏi một dòng JSON | Do `search_multi` gọi |
| `src/jssp/crawford.py` | **Sửa nhỏ**: thêm hàm `assumptions_for(L)` | Phần còn lại giữ nguyên |
| `src/jssp/search_multi.py` | **Sửa**: thêm hai cách `inc_descent`, `inc_binary` | Hai cách cũ giữ nguyên |
| `scripts/search_opt.py` | **Sửa**: thêm `--method inc_descent / inc_binary / inc_both / all` | |
| `tests/test_incremental.py` | **Mới**: 12 test | |
| `PROJECT_OVERVIEW.md` | **Cập nhật** | |

## Cách đưa vào dự án

1. Giải nén `day6-update.zip`.
2. Chép đè các file vào đúng thư mục tương ứng trong dự án (cùng cấu trúc `src/`, `scripts/`, `tests/`).
3. Mở terminal **ở thư mục chứa `scripts/`** và bật `.venv`.

## 3 lệnh chạy

**Lệnh 1: kiểm tra (test).**
```
python -m pytest -q
```
Mong đợi: khoảng **37 passed, 1 skipped**. Có hai test dùng PySAT thật (`glucose4` và `cadical153`), chúng chỉ chạy được trên máy bạn.

**Lệnh 2: chạy thử nhỏ, so cả 4 cách.**
```
python scripts/search_opt.py ft06 la01 --method all
```
Cả 4 cách phải ra **cùng một đáp án** (FT06 = 55, la01 = 666). Khác nhau chỉ ở số lần hỏi và thời gian.

**Lệnh 3: bài chính, FT10.**
```
python scripts/search_opt.py ft10 --method all
```
Đáp án phải là 930. Chạy lâu (descent mất vài phút). Nếu muốn nhanh chỉ so hai cách chia đôi: `--method binary` rồi `--method inc_binary`.

## Nếu gặp lỗi liên quan `cadical153`

Mình **chưa chạy được PySAT thật** trên máy của mình, nên chưa kiểm chứng được `cadical153` có nhận assumptions ổn không (một số bản PySAT hạn chế phần này). Nếu `inc_*` báo lỗi hoặc trạng thái `ERROR`, chạy lại với solver khác (hỗ trợ assumptions chắc chắn):
```
python scripts/search_opt.py ft06 --method inc_both --solver glucose4
```
Rồi cho mình xem thông báo lỗi.

## Đọc kết quả ở đâu

Vẫn là `results/raw/calls.csv` và `results/raw/summary.csv`. Cột `method` giờ có thêm `inc_descent`, `inc_binary`.
So sánh `binary` với `inc_binary` ở cột `n_calls` và `total_time` trong `summary.csv`.

## Khác biệt cần nhớ (để viết báo cáo)

- Incremental **không có timeout từng lần hỏi**, chỉ có timeout cho cả phiên (`--total-timeout`), vì solver sống chung một tiến trình.
- Bộ nhớ đỉnh được ghi **cho cả phiên**, nằm ở dòng cuối của phiên trong `calls.csv` và cột `max_peak_mem_mb` trong `summary.csv`.
- `encode_time` chỉ khác 0 ở lần hỏi đầu (vì chỉ sinh cnf một lần).
- Nếu phiên bị dừng giữa chừng (hết giờ/RAM), các lần đã xong vẫn được ghi lại, nên vẫn báo được khoảng [lo, hi].

## Việc kiểm tra mình đã làm

- So kết quả incremental với phép vét cạn trên bài ngẫu nhiên nhỏ, hỏi L theo **thứ tự ngẫu nhiên** (để chắc assumptions không "rò rỉ" sang lần sau).
- So với cách sinh cnf mới mỗi lần: ra cùng SAT/UNSAT.
- Cố ý làm hỏng hàm `assumptions_for` (nới lỏng sai) thì test **bắt được** lỗi.
- Giới hạn: các test này chạy bằng solver DPLL nhỏ (không tận dụng clause đã học). Phần chạy PySAT thật chỉ kiểm được trên máy bạn.
