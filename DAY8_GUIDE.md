# Ngày 8 (T10): Chạy hàng loạt trên bài vừa và lớn

## Mục đích

Đến giờ ta mới chạy bài **nhỏ** (FT06, la01–la05, FT10). Ở đó mọi cách đều xong trong vài chục giây, nên chưa thấy cách nào hơn rõ rệt. Câu hỏi thú vị nằm ở bài **vừa và lớn**: SAT có hết RAM không? CP-SAT có hết giờ không? Cách nào cho khoảng [cận dưới, cận trên] tốt hơn khi không giải xong?

Chạy tay từng bài từng cách sẽ mệt và dễ sai, nên ta có một **script chạy hàng loạt**, để máy chạy qua đêm.

## Script làm gì

- Nhận một danh sách bài và danh sách cách giải, chạy lần lượt, mỗi ô (bài × cách) có **cùng một ngân sách thời gian**.
- **Bỏ qua ô đã có kết quả** trong `summary.csv`, nên bị ngắt (tắt máy, Ctrl+C) rồi chạy lại **đúng lệnh cũ** là tiếp tục được.
- `--max-hours N`: sau N giờ thì dừng, không bắt đầu ô mới.
- `--dry-run`: chỉ in kế hoạch, **không chạy gì**.
- Tự giới hạn RAM mỗi ô ở 70% RAM máy bạn. Ô nào vượt thì ghi `MEMOUT` (cũng là một kết quả hợp lệ).
- Ghi thông tin máy (CPU, RAM, phiên bản thư viện) vào `results/raw/environment.txt`, để đưa vào báo cáo.

## Ba bậc bài (mình dự đoán độ khó, chưa đo trên máy bạn)

| Bậc | Bài | Ngân sách mỗi ô | Các cách mặc định |
|---|---|---|---|
| small | ft06, la01–05, ft10 | 600 giây | cả 5 cách (đã chạy xong, sẽ bị bỏ qua) |
| medium | la06, la11, la16, la21, abz5, abz6, orb01 | 900 giây | `inc_binary`, `binary`, `cpsat` |
| large | abz7, abz8, abz9, yn1–yn4 | 3600 giây | `inc_binary`, `cpsat` |

Bài hết giờ **không phải thất bại**: kết quả là khoảng [LB, UB] đã chứng minh/đạt được, giống Bảng 5 của bài báo. Bậc large ở đây cũng chính là các bài lớn trong bài báo.

Bậc large bỏ `binary` và các cách giảm dần vì chúng tốn nhiều lần hỏi, rất chậm trên bài lớn.

## File mới

| File | Việc |
|---|---|
| `src/jssp/suite.py` | Lập kế hoạch, bỏ qua ô đã chạy, chạy từng ô, ghi thông tin máy |
| `scripts/run_suite.py` | Lệnh bạn gõ |
| `tests/test_suite.py` | 6 test |
| `PROJECT_OVERVIEW.md` | Cập nhật |

Không sửa file cũ nào.

## Cách đưa vào dự án

Giải nén `day8-update.zip`, chép đè vào dự án (đúng `src/`, `scripts/`, `tests/`). Mở terminal ở thư mục chứa `scripts/`, bật `.venv`.

## Các lệnh

**Lệnh 1: test.**
```
python -m pytest -q
```
Mong đợi: khoảng **56 passed, 1 skipped**.

**Lệnh 2: xem kế hoạch bậc medium (không chạy gì).**
```
python scripts/run_suite.py --tier medium --dry-run
```
Kiểm tra: bài nào được liệt kê, bài nào báo `[bo qua] khong thay bai` (nếu thiếu file thì chạy lại `fetch_benchmarks.py`), và dòng cuối cho biết **số giờ tối đa** nếu ô nào cũng hết giờ.

**Lệnh 3: chạy thật bậc medium, tối đa 5 tiếng.**
```
python scripts/run_suite.py --tier medium --max-hours 5
```
Khi xong (hoặc bị dừng), gửi mình `results/raw/summary.csv` và `results/raw/environment.txt`.

Chạy tiếp phần dở: **gõ lại đúng lệnh trên**.

**Sau đó (khi medium xong), bậc large:**
```
python scripts/run_suite.py --tier large --max-hours 8
```
Mỗi ô có thể tốn tới 1 giờ, nên nên chia thành nhiều đêm.

## Trước khi để máy chạy qua đêm

- **Tắt chế độ ngủ**: Cài đặt, Hệ thống, Nguồn và pin, "Màn hình và ngủ", chọn Không bao giờ (khi cắm sạc), và cắm sạc.
- **Đóng file CSV trong Excel**: Windows khóa file và script không ghi được.
- **Không chạy hai phiên cùng lúc** (chúng ghi chung `summary.csv`).
- **Đừng dùng máy làm việc nặng** trong lúc chạy, vì sẽ làm sai lệch thời gian đo.
- Nếu RAM máy ít (dưới 16 GB), ô bài lớn của SAT nhiều khả năng ghi `MEMOUT`. Đây là kết quả thật và đáng báo cáo, đừng coi là lỗi.

## Lưu ý trung thực

- Danh sách bài trong từng bậc và ngân sách là **dự đoán của mình**. Nếu bậc medium chạy quá nhanh hoặc quá chậm, ta chỉnh lại bằng `--instances` và `--budget`.
- Phần chạy thật (PySAT, OR-Tools, hàng giờ liền) chỉ làm được trên máy bạn. Mình đã kiểm tra logic lập kế hoạch, bỏ qua ô đã chạy, dừng theo giờ phiên, và chạy lại sau khi bị ngắt bằng solver nhỏ và CP-SAT giả.
- Cách chạy này dùng **cận ban đầu đơn giản và lịch heuristic**, giống nhau cho mọi cách giải, nên so sánh công bằng. Với bài lớn, cận trên heuristic cách đáp án khá xa, làm cnf của SAT to hơn; đó là một hạn chế thật của cách làm, và là chỗ để cải tiến sau (cận chặt hơn).
