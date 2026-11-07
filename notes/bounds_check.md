# Đối chiếu cận (Bounds Check) cho các ma trận JSSP và JSPPR

Tài liệu này ghi chú lại nguồn gốc, đối chiếu và đánh giá độ chính xác của các giá trị cận dưới (LB), cận trên (UB) và giá trị tối ưu tuyệt đối (Optimal) đang sử dụng trong dự án, dựa trên hai nguồn tài liệu công bố chính.

## 1. Nguồn trích dẫn (References)
*   **[Koshimura2010]**: Koshimura, M., Nabeshima, H., Fujita, H., & Hasegawa, R. (2010). *Solving Open Job-Shop Scheduling Problems by SAT Encoding*. IEICE TRANSACTIONS on Information and Systems, 93(8), 2316-2318[cite: 45, 47].
*   **[Nguyen2026]**: Nguyen, H. T., Nguyen, D. T. K., & Van, K. T. (2026). *Exact SAT and Constraint Programming for Job Shop Scheduling with Time-Varying Peak Power Constraints*[cite: 21, 42].

---

## 2. Đối chiếu các bài toán JSSP Kinh điển (Dựa trên `known_bounds.csv` và Koshimura2010)

Hiện tại, file `data/known_bounds.csv` đang ghi nhận các giới hạn của những bài toán cổ điển (FT, LA, ABZ, YN). Sau khi đối chiếu với bài báo **[Koshimura2010]** (đặc biệt là Bảng 1, 4 và 5)[cite: 46, 47], ta có các kết luận sau:

### 2.1. Các bài toán đã được chứng minh tối ưu tuyệt đối (Optimal)
| Tên bài | Giá trị CSV | Trạng thái đối chiếu | Nguồn/Ghi chú |
| :--- | :--- | :--- | :--- |
| **ABZ9** | 678 | **Khớp hoàn toàn** | Được [Koshimura2010] chứng minh tối ưu bằng SAT Solver[cite: 47]. |
| **YN1** | 884 | **Khớp hoàn toàn** | Được [Koshimura2010] chứng minh tối ưu bằng SAT Solver[cite: 47]. |
| **FT06, FT10, FT20** | 55, 930, 1165 | **Khớp** | Đã được xác nhận tối ưu từ lâu trong tài liệu (CSV ghi `"literature"`)[cite: 46]. |
| **la01 - la05** | (Nhiều giá trị) | **Khớp** | Tối ưu chuẩn (CSV ghi `"literature"`)[cite: 46]. |
| **ABZ5, ABZ6** | 1234, 943 | **Khớp** | Tối ưu chuẩn (CSV ghi `"literature"`)[cite: 46]. |

### 2.2. Các bài toán mở (Mới chỉ có LB và UB)
Với các bài vẫn được gắn mác `open_2010` trong CSV, các giá trị hoàn toàn **KHỚP** với những giới hạn mới nhất do [Koshimura2010] tính toán ra:

| Tên bài | LB (Mới) | UB (Mới) | Đánh giá so với lịch sử |
| :--- | :--- | :--- | :--- |
| **ABZ8** | 659 | 665 | LB đã được cải thiện từ 646 lên 659 nhờ SAT[cite: 46, 47]. |
| **YN2** | 893 | 905 | Cải thiện cả hai cận (LB cũ là 870, UB cũ là 907)[cite: 46, 47]. |
| **YN3** | 880 | 892 | LB đã được cải thiện từ 840 lên 880 nhờ SAT[cite: 46, 47]. |
| **YN4** | 948 | 968 | LB đã được cải thiện từ 920 lên 948 nhờ SAT[cite: 46, 47]. |

---

## 3. Đối chiếu mở rộng: Biến thể JSPPR (Dựa trên Nguyen2026)

Tài liệu **[Nguyen2026]** cung cấp một đợt kiểm toán (audit) quy mô lớn đối với 35 bài benchmark của biến thể *Job Shop Scheduling Problem with Power Requirements (JSPPR)* do Kemmoe et al. (2017) từng công bố[cite: 21, 26, 34].

Nếu dự án của chúng ta mở rộng để chạy thử bộ dữ liệu JSPPR này, cần **đặc biệt lưu ý** các sai lệch nghiêm trọng của dữ liệu lịch sử như sau:

### 3.1. Các giới hạn tối ưu MỚI (Vượt qua GRASP ELS)
Phương pháp SAT và CP của [Nguyen2026] đã tìm ra 4 mốc makespan tối ưu mới, nhỏ hơn kết quả tốt nhất trước đây[cite: 36]:
*   **JSPPR_5_8x4**: Cập nhật từ 468 xuống **467**[cite: 36].
*   **JSPPR_4_9x4**: Cập nhật từ 639 xuống **638**[cite: 36].
*   **JSPPR_2_10x4**: Cập nhật từ 653 xuống **647**[cite: 36].
*   **JSPPR_4_10x4**: Cập nhật từ 680 xuống **657** (cải thiện đến 23 đơn vị)[cite: 36].

### 3.2. CẢNH BÁO: Các kết quả cũ bị LỆCH (Sai lệch cấu trúc / Vi phạm ràng buộc)
[Nguyen2026] phát hiện ra 7 bài trong công bố của Kemmoe có makespan *nhỏ hơn một cách phi lý* so với cận tối ưu toán học (do các lịch trình cũ đã vi phạm ràng buộc công suất nguồn điện tại một số thời điểm)[cite: 37, 41]. Khi sử dụng, ta phải dùng **Verified optimal (Cmax chuẩn)** thay vì Cmax báo cáo cũ:

| Tên bài (JSPPR) | Kết quả cũ (Lỗi) | Tối ưu chuẩn bằng SAT/CP | Mức chênh lệch |
| :--- | :--- | :--- | :--- |
| **JSPPR_3_4x4** | 298 | **343** | +45[cite: 37] |
| **JSPPR_3_5x4** | 374 | **423** | +49[cite: 37] |
| **JSPPR_3_6x4** | 459 | **479** | +20[cite: 37] |
| **JSPPR_3_7x4** | 495 | **512** | +17[cite: 37] |
| **JSPPR_3_8x4** | 527 | **528** | +1[cite: 37] |
| **JSPPR_1_9x4** | 579 | **602** | +23[cite: 37] |
| **JSPPR_3_9x4** | 558 | **581** | +23[cite: 37] |

*Ghi chú thêm từ [Nguyen2026]*: Ngoài vi phạm điện năng, 10 bài toán JSPPR có chứa dữ liệu lỗi (tham chiếu máy ảo số "4" trong khi cấu hình chỉ có 4 máy mang index 0,1,2,3), cần tiền xử lý loại bỏ khi đọc file benchmark[cite: 40].

## 4. Hành động
1.  Các giá trị hiện tại trong `data/known_bounds.csv` hoàn toàn đáng tin cậy. Nguồn `"literature"` ở các bài `ft` và `la` có thể giữ nguyên. Nguồn cho `abz8-9` và `yn1-4` đã được ghi chú chính xác là `Koshimura et al. 2010`.
2.  Nếu dự án tiếp tục thử nghiệm thêm bộ dữ liệu **JSPPR**, bắt buộc phải tạo một file `known_bounds_jsppr.csv` riêng với dữ liệu **Cmax chuẩn** từ Bảng 4 và Bảng 5 của [Nguyen2026] để không bị kiểm thử đánh giá sai (Fail/Mismatch) khi đối chiếu kết quả.