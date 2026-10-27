# Ngày 4 (T5–T6) – Kiểm thử theo đáp án đã biết + hình Gantt đầu tiên

## File (chép vào repo, giữ nguyên đường dẫn; run_sat.py thay bản cũ)
- `scripts/run_sat.py`      : thêm cờ `--json` (in 1 dòng kết quả cho script khác đọc)
- `scripts/verify_known.py` : với mỗi bài có tối ưu đã biết: S_opt phải SAT, S_(opt-1) phải UNSAT; sinh báo cáo

## Chạy (trong thư mục có README.md, đã kích hoạt .venv)
```powershell
pytest                                                    # vẫn 18 passed, 1 skipped
python scripts/verify_known.py --only ft06                # vài giây; mong đợi 2 dòng PASS
python scripts/verify_known.py --only la01 la02 la03 la04 la05
python scripts/run_sat.py data/ft06.txt --L 55 --gantt results/figures/ft06_55.png    # hình Gantt đầu tiên
python scripts/verify_known.py --only ft10 --timeout 1800 # có thể rất lâu (đến ~1 giờ/lần giải); chạy sau cùng
```
Kết quả được ghi vào `results/small_check.md` và `results/small_check.csv` (đây là "báo cáo kiểm thử nhỏ" của T6).

## Cách đọc cột "đánh giá"
| Giá trị | Nghĩa | Việc cần làm |
|---|---|---|
| PASS | đúng như đáp án đã biết | không |
| TIMEOUT | quá giờ, CHƯA kết luận (không phải lỗi) | ghi vào báo cáo như một giới hạn; tăng --timeout nếu muốn |
| MISMATCH: UNSAT dù đáp án đã biết khả thi | nghi lỗi mã hóa | dán kết quả cho mình |
| MISMATCH: có lịch ngắn hơn đáp án đã biết | lịch đó đã qua validate, nên nhiều khả năng giá trị trong `data/known_bounds.csv` sai (các giá trị "literature" là mình ghi từ trí nhớ) | đối chiếu nguồn công khai, sửa CSV |
| ERROR | script lỗi | dán dòng lỗi cho mình |

## Commit
```powershell
git add .
git commit -m "Day 4: known-optimum verification, first Gantt"
git push
```
