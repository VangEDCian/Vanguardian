# Research outline

## Generals

### Summary

Nghiên cứu ngẫu nhiên, nhãn mở, hai nhóm điều trị, hai giai đoạn, bắt chéo, liều đơn tiêm dưới da, so sánh dược động học, dược lực học và tính an toàn của `NANOKINE` do Công ty Cổ phần Công nghệ Sinh học Dược Nanogen sản xuất với `Eprex 4000 U` do Cilag AG sản xuất trên người tình nguyện khoẻ mạnh.

## Scientific and technological content of the research

### Research objectives

#### Main objectives

Đánh giá tương đương về dược động học (`PK`) và dược lực học (`PD`) giữa `NANOKINE` và `Eprex 4000 IU` trên người tình nguyện khoẻ mạnh.

#### Secondary objectives

Đánh giá tính an toàn giữa `NANOKINE` và `Eprex 4000 IU` trên người tình nguyện khoẻ mạnh.

### Research methods

#### Research design

- Thiết kế: ngẫu nhiên, nhãn mở, hai nhóm điều trị, hai giai đoạn, bắt chéo, liều đơn tiêm dưới da
- Quần thể nghiên cứu: 44 người tình nguyện khoẻ mạnh đủ điều kiện
- Tỷ lệ phân nhóm: `1:1`
- Sàng lọc: trong vòng `10 ngày` trước khi vào nghiên cứu
- Số lần dùng thuốc: `02 lần tiêm`, tương ứng `02 giai đoạn`
- Washout: `28 ngày` giữa lần tiêm 1 và lần tiêm 2
- Trình tự điều trị:
  - Giai đoạn 1: 22 đối tượng dùng `Eprex 4000 U`, 22 đối tượng dùng `NANOKINE`
  - Giai đoạn 2: hai nhóm đổi thuốc cho nhau theo thiết kế bắt chéo

#### Study flow and visit schedule

- `V0 / D-10`: sàng lọc, tư vấn và ký ICF, đánh giá đủ điều kiện tham gia
- `V1 / D1`: phân ngẫu nhiên, cấp mã/thẻ nghiên cứu, dùng thuốc nghiên cứu giai đoạn 1
- `V2 - V10 / D2, D3, D4, D5, D6, D7, D8, D10, D14`: theo dõi sau dùng thuốc giai đoạn 1
- `V11 / D29`: dùng thuốc nghiên cứu giai đoạn 2 sau washout 28 ngày
- `V12 - V20 / D30, D31, D32, D33, D34, D35, D36, D38, D42`: theo dõi sau dùng thuốc giai đoạn 2
- `FU / D52`: theo dõi qua điện thoại 10 ngày sau lần thăm khám cuối cùng; mời tái khám nếu cần

#### Assessments and data collection

Các hoạt động và dữ liệu cần được hỗ trợ trong E-CRF gồm:

- Tư vấn và ký `ICF`
- Nhân chủng học
- Tiền sử y khoa
- Tiền sử dùng thuốc
- Đo sinh hiệu
- Đánh giá phản ứng tại chỗ tiêm
- Khám lâm sàng
- Điện tâm đồ
- Tổng phân tích nước tiểu
- Xét nghiệm chất gây nghiện trong nước tiểu
- `HBsAg`, `HIV`, `anti-HCV`
- Đông máu
- Tổng phân tích tế bào máu, bao gồm `RET`
- Sinh hóa
- Xét nghiệm `PK`
- Xét nghiệm `PD`
- Tiêu chuẩn chọn/loại trừ
- Phân ngẫu nhiên
- Cấp thẻ nghiên cứu
- Tiêm sản phẩm nghiên cứu
- Ghi nhận bệnh lý phát sinh và điều trị
- Ghi nhận `AE/SAE`
- Thuốc dùng đồng thời
- Hướng dẫn đối tượng

#### Notes for safety and assessment handling

- `AE` được thu thập qua báo cáo tự nguyện của đối tượng hoặc qua hỏi bệnh/chăm khám của nghiên cứu viên.
- Đánh giá phản ứng tại chỗ tiêm được thực hiện hằng ngày trong 7 ngày đầu sau tiêm hoặc khi có bất thường tại vị trí tiêm.
- Kết quả `PD` từ `V1` đến `V20` cần bao gồm tất cả các chỉ số tổng phân tích tế bào máu, có `RET`.
- Quy trình cần hỗ trợ theo dõi sau nghiên cứu ở `D52` và khả năng phát sinh thăm khám thêm nếu cần.

#### PK and PD sampling implications

Theo bảng thời gian lấy mẫu trong synopsis, mỗi giai đoạn có lấy mẫu dày đặc từ trước tiêm đến `312 giờ` sau tiêm. Các mốc thể hiện trong tài liệu gồm các mốc ngay sau tiêm trong vài phút đầu và các mốc giờ kéo dài như `0.5`, `3`, `6`, `9`, `12`, `14`, `15`, `24`, `30`, `48`, `72`, `96`, `120`, `144`, `168`, `216`, `312`.

Điều này có nghĩa hệ thống phải hỗ trợ:

- visit schedule nhiều mốc thời gian trong mỗi giai đoạn
- biểu mẫu/lab form riêng cho `PK` và `PD`
- quản lý cửa sổ thời gian lấy mẫu
- phân biệt dữ liệu theo `period`, `visit`, `sample timepoint`

### Operational implications for system design

#### Core domain facts that should drive the implementation

- Mỗi đối tượng phải có một mã nghiên cứu duy nhất sau khi hoàn tất sàng lọc và xác nhận đủ điều kiện.
- Phân ngẫu nhiên xác định thứ tự sử dụng thuốc trong hai giai đoạn, không chỉ gán nhãn nhóm đơn giản.
- Đây là nghiên cứu bắt chéo, nên cùng một đối tượng sẽ nhận cả hai chế phẩm ở hai giai đoạn khác nhau.
- Thiết kế dữ liệu phải tách rõ `screening`, `period 1`, `washout`, `period 2`, `follow-up`.
- Hệ thống phải hỗ trợ cả dữ liệu theo lịch và dữ liệu phát sinh thêm khi đối tượng cần tái khám hoặc đánh giá ngoài kế hoạch.

#### Suggested E-CRF capability areas

- Quản lý hồ sơ đối tượng và eligibility
- Quản lý randomization và treatment sequence
- Quản lý visit schedule theo nhiều mốc ngày/giờ
- Ghi nhận dùng thuốc nghiên cứu theo từng giai đoạn
- Ghi nhận mẫu xét nghiệm `PK` và `PD`
- Ghi nhận xét nghiệm an toàn và thăm khám lâm sàng
- Ghi nhận `AE/SAE`, bệnh lý phát sinh và thuốc dùng đồng thời
- Hỗ trợ audit trail cho mọi thay đổi liên quan dữ liệu lâm sàng
