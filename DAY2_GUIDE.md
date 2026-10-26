# Ngày 2 – Parser và dữ liệu benchmark

## Có gì mới (chép đè vào repo của bạn, giữ nguyên đường dẫn)
- `scripts/fetch_benchmarks.py` : tải jobshop1.txt từ OR-Library, tách thành `data/instances/<tên>.txt`
- `src/jssp/info.py`            : in thông tin một bài (kích thước, LB/UB đơn giản)
- `data/known_bounds.csv`       : cận/tối ưu đã biết (ghi nguồn; cột source nói rõ chỗ nào cần tự đối chiếu)
- `tests/test_benchmarks.py`    : kiểm tra mọi file dữ liệu hợp lệ + script tách file

## Việc bạn làm (trong thư mục jssp-sat có README.md, đã kích hoạt .venv)
```powershell
pytest                                   # mong đợi: 9 passed
python scripts/fetch_benchmarks.py       # tải và tách bài
python src/jssp/info.py data/instances/ft10.txt
pytest                                   # chạy lại: giờ kiểm tra cả các file vừa tải
```
Nếu tải lỗi: mở http://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/jobshop1.txt, lưu thành jobshop1.txt, rồi
`python scripts/fetch_benchmarks.py --from-file jobshop1.txt`.

## Cần tự đối chiếu
- `known_bounds.csv`: các dòng "literature" mình ghi từ trí nhớ; hãy đối chiếu với một nguồn công khai (vd. kho JSPLIB / trang optimizizer) trước khi đưa vào báo cáo.
- Bài ta01...: không có trong jobshop1.txt, tải sau nếu cần.

## Commit
```powershell
git add .
git commit -m "Day 2: benchmark fetcher, info tool, bounds, tests"
git push
```
