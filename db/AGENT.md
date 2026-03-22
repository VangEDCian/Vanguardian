# DB AGENT.MD

## Mục tiêu

Thư mục `db/` là nơi quản lý mô hình dữ liệu logic và lịch sử thay đổi schema cho hệ thống EDC của dự án.

Mục tiêu bắt buộc:

- Duy trì `db/dbdiagram.dbml` như nguồn mô tả logic schema rõ ràng, nhất quán và đọc được.
- Đảm bảo quan hệ dữ liệu luôn nguyên vẹn, cardinality rõ ràng, không tạo bảng mồ côi hoặc quan hệ mập mờ.
- Phản ánh đầy đủ thông tin hệ thống và thông tin nghiệp vụ, không chỉ mô hình hóa nhu cầu kỹ thuật thuần túy.
- Mỗi lần cập nhật `db/dbdiagram.dbml` có ảnh hưởng đến schema phải đi kèm migration hợp lý trong `db/migrations/`.
- Không cho phép lệch nhau giữa tài liệu nghiệp vụ, `dbdiagram.dbml`, và migration SQL.

## Tài liệu bắt buộc phải đọc trước khi sửa schema

Trước khi tạo mới hoặc chỉnh sửa `db/dbdiagram.dbml`, bắt buộc phải đọc toàn bộ các file hiện có trong thư mục `docs/` và đối chiếu với định hướng của dự án.

Tối thiểu phải đọc:

- `docs/research-outline.md`
- `docs/folder-tree.md`
- `src/AGENT.md`

Quy tắc bắt buộc:

- Không được sửa schema chỉ dựa trên suy đoán từ tên bảng, tên module hoặc yêu cầu kỹ thuật rời rạc.
- Nếu nghiệp vụ trong `docs/` chưa đủ rõ để ra quyết định về table, field, relation, enum, lifecycle hoặc nullability, phải dừng và làm rõ trước khi sửa.
- Nếu thiếu thông tin cần thiết để ra quyết định schema đúng, phải hỏi lại người yêu cầu trước khi thực hiện.
- Nếu có xung đột giữa `docs/` và mô hình hiện tại trong `dbdiagram.dbml`, ưu tiên kiểm tra lại nghiệp vụ trước khi chạm vào migration.

## Vai trò của từng file trong `db/`

- `db/dbdiagram.dbml`: nguồn mô tả logic schema hiện tại của hệ thống
- `db/migrations/*.sql`: lịch sử thay đổi schema theo từng bước, có thứ tự thời gian rõ ràng
- `db/AGENT.md`: quy ước bắt buộc khi phân tích, cập nhật hoặc review mô hình dữ liệu

## Nguyên tắc mô hình hóa dữ liệu

### 1) Ưu tiên sự thật nghiệp vụ

- Schema phải phản ánh được thực thể, trạng thái, vòng đời và quan hệ nghiệp vụ thật sự của nghiên cứu lâm sàng.
- Phải mô hình hóa rõ các vùng nghiệp vụ như `identity`, `study`, `crf`, `datacapture`, `reconcile`, `audit`, `governance`, `exporting`, `dashboard`, `core` khi chúng xuất hiện trong dữ liệu.
- Không nhồi nhiều khái niệm nghiệp vụ khác nhau vào cùng một bảng chỉ để giảm số lượng bảng.
- Không tạo bảng trung gian hoặc cột kỹ thuật nếu không giải thích được ý nghĩa nghiệp vụ của chúng.

### 2) Ownership và boundary phải rõ

- Mỗi bảng phải có owner context rõ ràng.
- Bảng nào thuộc context nào phải thể hiện được qua tên, note hoặc nhóm logic trong `dbdiagram.dbml`.
- Không dùng schema vật lý chung như lý do để làm mờ boundary giữa các bounded context.
- Nếu có quan hệ xuyên context, phải thể hiện rõ bảng nào là owner dữ liệu và vì sao quan hệ đó hợp lệ.

### 3) Quan hệ phải đầy đủ và nguyên vẹn

- Mọi foreign key phải phản ánh đúng nghiệp vụ và đúng cardinality `1-1`, `1-n`, `n-n`.
- Quan hệ nhiều-nhiều phải đi qua bảng nối rõ nghĩa nghiệp vụ, không dùng bảng nối vô danh.
- Không để tồn tại bảng con mà không có cơ chế liên kết rõ ràng tới aggregate hoặc parent phù hợp.
- Unique constraint, composite key, index và nullability phải được khai báo có chủ đích, không để mặc định theo cảm tính.
- Trường hợp không thể dùng foreign key vật lý vì lý do boundary hoặc lifecycle, phải ghi chú rõ trong `dbdiagram.dbml`.

### 4) Dữ liệu phải đủ thông tin hệ thống và thông tin nghiệp vụ

Khi thiết kế bảng, phải phân biệt và giữ đủ:

- thông tin định danh
- thông tin nghiệp vụ chính
- trạng thái/vòng đời
- quan hệ tham chiếu
- thông tin audit cần thiết
- thông tin thời gian có ý nghĩa nghiệp vụ

Không được chỉ giữ các cột kỹ thuật như `id`, `created_at`, `updated_at` mà bỏ mất meaning của dữ liệu lâm sàng, visit, period, randomization, PK/PD, AE/SAE, eligibility hoặc workflow vận hành.

## Quy tắc cập nhật `db/dbdiagram.dbml`

Mỗi lần cập nhật phải làm theo thứ tự:

1. Đọc lại tất cả file trong `docs/` và phần liên quan trong `src/AGENT.md`.
2. Xác định bounded context, aggregate, entity, workflow và quan hệ bị ảnh hưởng.
3. Cập nhật `db/dbdiagram.dbml` trước để phản ánh mô hình đích.
4. Kiểm tra lại:
   - bảng nào mới
   - bảng nào đổi cột
   - bảng nào đổi quan hệ
   - bảng nào cần unique/index/check
   - thay đổi nào có nguy cơ làm mất dữ liệu
5. Tạo migration SQL mới tương ứng trong `db/migrations/`.
6. Đảm bảo migration và `dbdiagram.dbml` mô tả cùng một trạng thái schema.

## Quy tắc viết `db/dbdiagram.dbml`

- Tên bảng phải rõ nghĩa nghiệp vụ, tránh viết tắt khó đoán.
- Tên cột phải ổn định, đọc được, nhất quán theo cùng một ngôn ngữ đặt tên.
- Mỗi bảng quan trọng nên có `Note` hoặc mô tả ngắn khi ý nghĩa nghiệp vụ không hiển nhiên.
- Với bảng nối, phải nói rõ vai trò nghiệp vụ, không tạo bảng nối kiểu generic.
- Enum hoặc status phải phản ánh lifecycle thật sự, không dùng trạng thái mơ hồ như `active/inactive` nếu nghiệp vụ cần chi tiết hơn.
- Những thực thể có timeline nghiên cứu như screening, period, visit, sample, dosing, follow-up phải được mô hình hóa sao cho truy vết được theo dòng thời gian nghiệp vụ.

## Quy tắc viết migration

### 1) Mỗi thay đổi schema phải có migration mới

- Mỗi lần thay đổi `db/dbdiagram.dbml` làm thay đổi schema, phải tạo một file SQL mới trong `db/migrations/`.
- Không sửa lại migration cũ đã được coi là lịch sử, trừ khi migration đó chưa từng được dùng và team thống nhất rõ.
- Tên file migration nên theo dạng:
  - `YYYYMMDD_short_description.sql`

### 2) Migration phải an toàn và có thứ tự

- Câu lệnh phải được sắp theo thứ tự tránh vi phạm dependency.
- Tạo bảng cha trước, bảng con sau.
- Tạo dữ liệu backfill hoặc default trước khi siết `NOT NULL` nếu cần.
- Tạo constraint/index ở thời điểm hợp lý, không làm migration tự mâu thuẫn.
- Nếu thay đổi có nguy cơ phá dữ liệu hoặc downtime, phải tách thành nhiều bước thay vì làm một lần.

### 3) Migration phải phản ánh đầy đủ ý định thay đổi

Migration không chỉ thêm cột hay bảng cho đủ chạy. Migration phải bao gồm đầy đủ những gì schema logic yêu cầu:

- create/alter/drop table
- create/alter/drop column
- foreign key
- unique constraint
- index
- default/backfill khi cần
- đổi tên hoặc tách cột theo chiến lược an toàn nếu có migration phá vỡ tương thích

## Checklist trước khi hoàn tất một thay đổi schema

Trước khi coi một thay đổi là xong, phải tự kiểm tra:

- Đã đọc lại toàn bộ file trong `docs/` chưa
- `db/dbdiagram.dbml` đã phản ánh đúng nghiệp vụ chưa
- Quan hệ giữa các bảng đã đủ và đúng cardinality chưa
- Có bảng hoặc cột nào chưa giải thích được ý nghĩa nghiệp vụ không
- Có bỏ sót owner context hoặc boundary nào không
- Có thay đổi nào chưa được ghi bằng migration SQL không
- Migration có nguy cơ làm mất dữ liệu, tạo orphan row hoặc phá referential integrity không
- `dbdiagram.dbml` và migration SQL có còn lệch nhau không

## Quy tắc khi thiếu thông tin

- Nếu thiếu thông tin nghiệp vụ, không tự ý chốt schema chỉ để hoàn thành nhanh.
- Nếu thiếu thông tin quan trọng, phải dừng và hỏi lại người yêu cầu trước khi sửa `db/dbdiagram.dbml` hoặc tạo migration mới.
- Nếu có nhiều khả năng modeling hợp lý, chọn phương án bảo toàn nghiệp vụ, auditability và tính nhất quán dữ liệu cao hơn.
- Nếu chưa đủ cơ sở để quyết định relation hoặc lifecycle, phải ghi nhận vấn đề và làm rõ trước khi tiếp tục sửa `dbdiagram.dbml`.
