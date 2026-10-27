# Ghi chú cài đặt mã hóa Crawford (ngày 3)

## Quy ước chỉ số (khác bài báo một chút)
Job l, thao tác i, thời gian t đều đánh số từ 0 (bài báo từ 1). Biến `sa`, `eb` có t = 0..L (đã đối chiếu: số biến
= n_pr + 2·(số thao tác)·(L+1) khớp đúng Bảng 2 của bài báo, ABZ9 N=661 -> 403.180 biến).

## Quy tắc -> code (src/jssp/crawford.py, hàm CrawfordEncoder._build)
| Quy tắc | Clause | Khối code |
|---|---|---|
| R1 | pr[(l,i),(l,i+1)] | `# R1` |
| R2 | pr[a,b] v pr[b,a], a,b cùng máy khác job | `# R2` |
| R3 | sa[a, head(a)] | `# R3` |
| R4 | eb[a, L - tail(a)] | `# R4` |
| R5 | sa[a,t] -> sa[a,t-1], 1<=t<=L | `# R5` |
| R6 | eb[a,t] -> eb[a,t+1], 0<=t<L | `# R6` |
| R7 | sa[a,t] -> NOT eb[a,t+p-1], 0<=t<=L-p | `# R7` |
| R8 | sa[a,t] ^ pr[a,b] -> sa[b,t+p_a], 0<=t<=L-p_a | `# R8` |
| R9 | NOT sa[a,t], L-p+1<=t<=L  (**bổ sung của nhóm**) | `# R9` |

## R9: vì sao thêm, và mức độ chắc chắn
Khi chỉ dùng R1–R8 đúng như mình đọc từ bài báo (R7 chạy t <= L-p), bài tay 2x2 (tối ưu = 7) vẫn cho S_6 là
"thỏa", và lịch giải mã ra có makespan 7 > 6 (test `test_eight_paper_rules_alone_are_unsound_at_boundary`).
Nguyên nhân: với thao tác cuối của job, nếu không có R9 thì không clause nào cấm sa[L-p+1..L] đúng.
R9 là hệ quả hiển nhiên của ngữ nghĩa ("bắt đầu >= t mà t > L-p thì kết thúc > L") nên không làm mất nghiệm hợp lệ nào.
**Lưu ý trung thực:** kết luận "bài báo thiếu" chỉ đúng với CÁCH ĐỌC của mình về miền chỉ số của R7; bản gốc có thể
ngầm hiểu khác. Trong báo cáo nên viết là "chúng tôi bổ sung R9 để đảm bảo tính đúng đắn của giải mã", kèm
thí nghiệm trên (có thể dùng bài tay làm ví dụ), không nên khẳng định bài báo sai.

## Đã kiểm chứng gì
- Với bài ngẫu nhiên nhỏ (tới 4 job x 3 máy, 60+ bài): S_opt thỏa, S_{opt-1} không thỏa, đối chiếu phép vét cạn;
  mọi nghiệm giải mã qua `validate_schedule`.
- Tăng trưởng mỗi bước L: +2·nops biến, +3·nops + n_pr clause (ABZ9: +600 / +6.880; YN1: +800 / +9.180 — đúng
  số trong Bảng 2, 3 của bài báo).
- CHƯA kiểm chứng trên FT06 với PySAT thật (môi trường dev không cài được PySAT): bạn chạy giúp, xem DAY3_GUIDE.md.
