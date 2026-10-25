# Ghi chú bài báo – Koshimura et al. 2010 (Crawford encoding)

## Bài toán
n job, m máy. Job l = chuỗi thao tác O^l_1..O^l_{q_l} theo thứ tự; mỗi thao tác dùng 1 máy cố định,
chạy liên tục p^l_i đơn vị. Mỗi máy 1 việc/lúc. Mục tiêu: min makespan.

## Ý tưởng
Tối ưu -> quyết định: S_L thỏa <=> tồn tại lịch có makespan <= L.
Tìm k sao cho S_{k-1} UNSAT và S_k SAT => optimum = k.

## Biến (t chạy 0..L)
- pr[l,i,k,j]  : O^l_i đứng TRƯỚC O^k_j
- sa[l,i,t]    : O^l_i bắt đầu >= t     (start at/after t)
- eb[l,i,t]    : O^l_i kết thúc <= t    (end by t)

## 8 quy tắc (clause)
1. pr[l,i,l,i+1]                                  (thứ tự trong job)
2. (cùng máy) pr[l,i,k,j] v pr[k,j,l,i]           (không chồng nhau)
3. sa[l,i,t], t = sum_{u<i} p^l_u                 (unit: cận dưới start)
4. eb[l,i,t], t = L - sum_{u>i} p^l_u             (unit: cận trên end)
5. sa[l,i,t] -> sa[l,i,t-1]                       (đơn điệu)
6. eb[l,i,t] -> eb[l,i,t+1]                       (đơn điệu)
7. sa[l,i,t] -> NOT eb[l,i,t+p^l_i-1]             (độ dài thao tác)
8. sa[l,i,t] ^ pr[l,i,k,j] -> sa[k,j,t+p^l_i]     (gắn thứ tự với thời gian)

## Giải mã
start(l,i) = max{ t : sa[l,i,t] = True }.

## Kết quả bài báo
ABZ9 = 678, YN1 = 884 (tối ưu). Cải thiện cận: ABZ8 LB 659; YN2 [893,905]; YN3 LB 880; YN4 LB 948.
Solver: MiniSat 2. Kích thước CNF tăng tuyến tính theo L, thời gian tăng mũ. UNSAT sát điểm chuyển khó nhất.

## Hạn chế
RAM 8GB, thời gian (YN1 S_884 ~36 ngày), MiniSat tuần tự, chỉ một cách mã hóa.

## Việc cần kiểm tra khi cài đặt (CHƯA chắc từ bài báo)
- Miền chỉ số t cụ thể của quy tắc 5,6,8 (cần đọc kỹ bài báo gốc, tránh lệch 1).
- Quy tắc 8 chỉ sinh khi t + p <= L.
