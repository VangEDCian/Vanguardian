# Subject Status Rules cho EDC

## Mục đích

Tài liệu này định nghĩa rule nghiệp vụ cho `subject status` trong hệ thống EDC.

Mục tiêu:

- chuẩn hóa cách hiểu các trạng thái của subject trong nghiên cứu lâm sàng
- tránh dùng lẫn lộn giữa `Enrolled` và `Randomized`
- xác định các trạng thái kết thúc sớm hoặc hoàn tất
- quy định metadata bắt buộc khi subject được randomization
- hỗ trợ implementation nhất quán trong module `study`, `reconcile`, `audit`, `governance`, `dashboard`, và `exporting`

---

## Phạm vi

Rule này áp dụng cho:

- study có quản lý subject lifecycle trong EDC
- study có hoặc không có randomization
- study có screening, enrollment, completion, withdrawal/discontinuation
- study randomized cần lưu đầy đủ metadata randomization

---

## Danh sách trạng thái chuẩn

Subject status chuẩn trong hệ thống gồm:

- `Screened`
- `Enrolled`
- `Randomized`
- `ScreenFailure`
- `Completed`
- `Withdrawn`
- `Discontinued`

> Ghi chú: `Withdrawn` và `Discontinued` có thể được triển khai thành hai status riêng hoặc một nhóm status cùng loại “dừng sớm”, tùy protocol và data model của study. Nếu gộp logic, vẫn phải giữ được lý do dừng sớm và audit trail rõ ràng.

---

## Định nghĩa từng trạng thái

### `Screened`

Đã được sàng lọc, nhưng chưa chắc đủ điều kiện.

Ý nghĩa nghiệp vụ:

- subject đã đi vào quy trình screening
- đã có screening activity hoặc screening record
- chưa mặc định đồng nghĩa với eligible
- chưa mặc định đồng nghĩa với enrolled

### `Enrolled`

Tùy study, đôi khi chỉ nghĩa là đã được nhận vào nghiên cứu, nhưng chưa chắc đã randomize.

Một số protocol dùng `Enrolled` trước `Randomized`, một số nơi gần như xem hai khái niệm này rất sát nhau. Phải đọc định nghĩa cụ thể của study.

Ý nghĩa nghiệp vụ:

- subject đã được nhận vào nghiên cứu theo định nghĩa của protocol
- có thể đã consent và đủ điều kiện vào study
- không được tự động suy ra đã randomize

### `Randomized`

Đã được phân nhóm ngẫu nhiên.

Ý nghĩa nghiệp vụ:

- subject đã được gán treatment arm, group, hoặc sequence theo randomization schedule / IRT / IWRS / quy trình study
- đây là một mốc nghiệp vụ riêng, không được đồng nhất ngầm với `Enrolled`
- với crossover study, randomization thường gắn với `sequence`, ví dụ `AB` hoặc `BA`

### `ScreenFailure`

Không đạt điều kiện, không vào nghiên cứu.

Ý nghĩa nghiệp vụ:

- subject đã trải qua screening nhưng không tiếp tục vào nghiên cứu
- đây là trạng thái kết thúc sớm trước khi thực sự vào study theo protocol

### `Completed`

Đã hoàn tất nghiên cứu.

Ý nghĩa nghiệp vụ:

- subject đã hoàn tất toàn bộ hành trình nghiên cứu theo protocol hoặc theo định nghĩa completion của study
- đây là trạng thái kết thúc thành công của subject lifecycle

### `Withdrawn`

Đã vào nghiên cứu nhưng dừng sớm.

Ý nghĩa nghiệp vụ:

- subject chủ động rút khỏi nghiên cứu hoặc consent bị rút lại theo định nghĩa study
- là trạng thái kết thúc sớm sau khi subject đã vào nghiên cứu

### `Discontinued`

Đã vào nghiên cứu nhưng dừng sớm.

Ý nghĩa nghiệp vụ:

- subject bị ngừng tham gia nghiên cứu hoặc treatment/follow-up bị dừng theo lý do nghiệp vụ hoặc y khoa
- là trạng thái kết thúc sớm sau khi subject đã vào nghiên cứu

> Nếu study không tách rõ `Withdrawn` và `Discontinued`, hệ thống vẫn phải lưu reason code hoặc disposition reason để phục vụ audit, reporting và export.

---

## Nguyên tắc tổng quát

### Rule S1 — Subject status là lifecycle business state

`subject status` là trạng thái nghiệp vụ của subject trong study lifecycle.

Nó không phải:
- UI label tạm thời
- derived text không kiểm soát
- trạng thái tính bằng client-side logic

### Rule S2 — Mỗi subject tại một thời điểm chỉ có một current status chính

Tại một thời điểm, subject chỉ có một `current_status` chính thức.

Nếu cần lưu lịch sử:
- phải có status history
- phải có timestamp
- phải có actor/source
- phải có audit trail

### Rule S3 — Không được suy diễn ngầm giữa `Enrolled` và `Randomized`

Không được mặc định:
- `Enrolled` => `Randomized`
- `Randomized` => `Enrolled`

Việc mapping hai trạng thái này phải theo định nghĩa cụ thể của protocol/study.

### Rule S4 — Terminal status phải được kiểm soát chặt

Các trạng thái sau được xem là terminal hoặc gần-terminal theo lifecycle:

- `ScreenFailure`
- `Completed`
- `Withdrawn`
- `Discontinued`

Sau khi subject vào các trạng thái này:
- không được chuyển trạng thái tùy tiện
- mọi reopen/reverse phải có rule rõ ràng của study
- mọi thay đổi phải có audit trail bắt buộc

---

## Rule chuyển trạng thái

## Allowed baseline flow

Luồng điển hình có thể là:

`Screened -> Enrolled -> Randomized -> Completed`

Các nhánh kết thúc sớm có thể gồm:

- `Screened -> ScreenFailure`
- `Enrolled -> Withdrawn`
- `Enrolled -> Discontinued`
- `Randomized -> Withdrawn`
- `Randomized -> Discontinued`

> Ghi chú: flow thực tế phụ thuộc protocol. Hệ thống phải cho phép cấu hình hoặc policy hóa transition nếu study yêu cầu khác.

### Rule T1 — `Screened` là điểm bắt đầu chuẩn

Nếu study có screening, subject nên bắt đầu ở `Screened`.

Không được nhảy thẳng vào `Completed`, `Withdrawn`, `Discontinued`, hoặc `Randomized` nếu chưa có căn cứ nghiệp vụ hợp lệ.

### Rule T2 — `ScreenFailure` chỉ hợp lệ khi subject chưa thực sự vào nghiên cứu

`ScreenFailure` không được dùng cho subject đã thực sự bước vào treatment/randomization lifecycle, trừ khi protocol định nghĩa khác và có review kiến trúc/nghiệp vụ rõ ràng.

### Rule T3 — `Randomized` chỉ hợp lệ khi study hỗ trợ randomization

Không được set `Randomized` nếu:
- study không phải randomized study
- study chưa có randomization process
- thiếu metadata randomization bắt buộc

### Rule T4 — `Completed` chỉ hợp lệ khi subject đã hoàn tất theo định nghĩa study

Không được set `Completed` nếu:
- subject còn ở screening phase
- subject còn đang ở trạng thái không hoàn tất required journey theo protocol
- policy reconcile/governance cấm completion khi dữ liệu chưa đạt điều kiện bắt buộc

### Rule T5 — `Withdrawn` / `Discontinued` phải có lý do

Khi subject chuyển sang:
- `Withdrawn`
- `Discontinued`

phải lưu thêm:
- transition datetime
- actor/source
- reason code hoặc free-text reason theo policy study
- audit trail bắt buộc

---

## Metadata bắt buộc cho randomization

Khi `subject_status = Randomized`, hệ thống phải lưu thêm tối thiểu các trường sau:

- `randomization_status`
- `randomization_datetime`
- `randomization_sequence`
- `randomization_number`
- `randomized_by`
- `randomization_source`

### Ý nghĩa từng trường

#### `randomization_status`
Trạng thái nghiệp vụ liên quan tới randomization.

Ví dụ có thể là:
- `Pending`
- `Assigned`
- `Confirmed`
- `Failed`
- `Cancelled`

> Tập giá trị cụ thể nên do study hoặc domain policy định nghĩa rõ.

#### `randomization_datetime`
Thời điểm subject được randomize.

#### `randomization_sequence`
Sequence hoặc treatment assignment được gán cho subject.

Ví dụ:
- `A`
- `B`
- `AB`
- `BA`

#### `randomization_number`
Số randomization hoặc allocation number của subject.

#### `randomized_by`
Actor hoặc hệ thống thực hiện randomization.

Ví dụ:
- username
- service name
- IWRS user
- system account

#### `randomization_source`
Nguồn phát sinh randomization.

Ví dụ:
- `manual`
- `system`
- `iwrs`
- `irt`
- `import`

---

## Rule dữ liệu cho randomization

### Rule R1 — Không được thiếu metadata randomization khi status là `Randomized`

Nếu `subject_status = Randomized`, các trường randomization bắt buộc không được rỗng nếu protocol yêu cầu.

Tối thiểu phải review các trường:
- `randomization_datetime`
- `randomization_sequence`
- `randomization_number`
- `randomized_by`
- `randomization_source`

### Rule R2 — Randomization metadata phải cùng study context với subject

Không được gán sequence hoặc number thuộc study khác hoặc scheme khác.

### Rule R3 — Randomization metadata phải có audit trail

Mọi thay đổi đối với:
- `randomization_status`
- `randomization_datetime`
- `randomization_sequence`
- `randomization_number`
- `randomized_by`
- `randomization_source`

đều phải có audit trail.

### Rule R4 — Với crossover study, `randomization_sequence` là field bắt buộc quan trọng

Đối với study bắt chéo:
- phải lưu sequence rõ ràng
- không được chỉ lưu mỗi status `Randomized`
- sequence là phần cốt lõi của business meaning

---

## Ownership theo module

### `study`
Sở hữu:
- subject lifecycle state
- subject status hiện tại
- status transition chính
- randomization metadata ở mức subject lifecycle nếu đó là phần canonical state

### `reconcile`
Không sở hữu `subject status`, nhưng có thể:
- consume status để kiểm tra readiness
- dùng status trong discrepancy/query workflow
- không được update trực tiếp private persistence của `study` nếu không qua public contract

### `audit`
Sở hữu audit trail cho:
- status transition
- randomization metadata changes
- disposition changes

### `governance`
Có thể áp policy về:
- ai được phép chuyển sang `Completed`
- ai được phép sửa randomization metadata
- masking/export rule liên quan subject disposition

### `dashboard`
Được dùng subject status để build KPI/read model:
- screened count
- enrolled count
- randomized count
- completed count
- withdrawn/discontinued count
- screen failure count

### `exporting`
Dùng subject status và randomization metadata cho:
- operational exports
- subject disposition report
- CDISC/supporting export nếu áp dụng

### `core`
Chỉ chứa primitive ổn định dùng chung như:
- `SubjectId`
- enum base abstractions
- result/error primitives

Không chứa toàn bộ logic lifecycle của subject status.

---

## Audit trail bắt buộc

Mọi thay đổi sau phải sinh audit trail:

- thay đổi `subject_status`
- thay đổi randomization metadata
- thay đổi withdrawal/discontinuation reason
- mọi reverse/reopen của terminal status nếu được phép

Audit trail tối thiểu nên có:
- subject id
- study id
- actor
- action
- before value
- after value
- datetime
- source
- reason/comment nếu policy yêu cầu

---

## Điều không được làm

- Không dùng string status tự do ngoài tập giá trị chuẩn nếu chưa được study policy cho phép.
- Không suy luận `Randomized` chỉ vì study là randomized study.
- Không bỏ qua metadata randomization khi subject đã randomize.
- Không update `subject status` trực tiếp từ module khác mà bypass contract của `study`.
- Không dùng template/UI text làm source of truth cho lifecycle state.
- Không đổi terminal status mà không có audit trail.

---

## Khuyến nghị triển khai kỹ thuật

- Định nghĩa `SubjectStatus` là enum/value object rõ ràng.
- Tách `current_status` và `status_history`.
- Tạo use case riêng cho từng transition quan trọng:
  - `MarkSubjectScreened`
  - `EnrollSubject`
  - `RandomizeSubject`
  - `MarkScreenFailure`
  - `CompleteSubject`
  - `WithdrawSubject`
  - `DiscontinueSubject`
- Với `RandomizeSubject`, validate đầy đủ randomization metadata trước khi commit.
- Nếu study-specific rule khác chuẩn chung, phải cấu hình bằng policy hoặc documented exception, không hard-code tùy tiện trong UI.

---

## Mẫu fields gợi ý

```text
subject_status
subject_status_datetime
subject_status_reason_code
subject_status_reason_text

randomization_status
randomization_datetime
randomization_sequence
randomization_number
randomized_by
randomization_source
```

---

## Rule ngắn gọn để dán vào AGENT.MD

- Subject status chuẩn gồm: `Screened`, `Enrolled`, `Randomized`, `ScreenFailure`, `Completed`, `Withdrawn`, `Discontinued`.
- `Enrolled` và `Randomized` không được đồng nhất ngầm; phải theo protocol của study.
- Nếu subject ở trạng thái `Randomized`, phải lưu đầy đủ randomization metadata theo policy study.
- `ScreenFailure`, `Completed`, `Withdrawn`, `Discontinued` là các trạng thái kết thúc hoặc gần-kết thúc và phải có kiểm soát chặt.
- Mọi thay đổi subject status và randomization metadata đều phải có audit trail.
- Module `study` là owner của subject lifecycle state; các module khác không được bypass contract để sửa trực tiếp.
