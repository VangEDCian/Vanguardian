# AGENT.MD

## Mục tiêu
Kho mã này là nền tảng phát triển hệ thống EDC theo hướng DDD, bounded context rõ ràng, ưu tiên tính toàn vẹn dữ liệu, auditability, và khả năng mở rộng nghiệp vụ nghiên cứu lâm sàng.

Tài liệu này là quy ước làm việc bắt buộc cho tất cả kỹ sư tham gia dự án.

---

## 1) Nguyên tắc kiến trúc

### 1.1. Kiến trúc tổng thể
- Kiến trúc mặc định là **Modular Monolith**.
- Không tách microservice khi chưa có áp lực nghiệp vụ, hiệu năng, hoặc tổ chức đủ rõ.
- Mỗi bounded context là một module độc lập về ngôn ngữ, use case, rule và persistence boundary.
- Giao tiếp giữa context thông qua:
  - application service contract nội bộ,
  - domain event,
  - integration event nội bộ,
  - read model.
- Không cho phép context này đọc trực tiếp aggregate nội bộ của context khác.

### 1.2. Kiểu kiến trúc trong từng context
Mỗi bounded context đóng gói theo hướng:
- `domain/`
- `application/`
- `infrastructure/`
- `presentation/` (nếu có web/API adapter riêng)

Cho phép áp dụng Clean Architecture ở **bên trong từng bounded context**, không áp đặt clean architecture ở mức toàn repo theo kiểu quá cơ học.

### 1.3. Quy tắc ưu tiên
Khi có xung đột, ưu tiên theo thứ tự:
1. Tính đúng nghiệp vụ nghiên cứu lâm sàng
2. Audit trail và compliance
3. Tính nhất quán dữ liệu
4. Tách boundary rõ
5. Đơn giản trong triển khai
6. Tối ưu kỹ thuật

---

## 2) Bounded Context chính

### Generic
- `identity_access`
- `user_administration`

### Core Domain
- `study_design`
- `study_operations`
- `clinical_capture`
- `query_management`
- `data_review`

### Supporting / Compliance
- `audit_compliance`
- `reporting_export`
- `operational_tracking`

### Shared
- `shared_kernel`

---

## 3) Ý nghĩa từng context

### `identity_access`
Chịu trách nhiệm:
- login/logout
- credential
- session/token
- password policy
- authorization runtime check

Không chứa workflow quản trị user ở mức admin.

### `user_administration`
Chịu trách nhiệm:
- tạo/sửa/khóa user
- gán role
- gán site/study membership
- quản trị hồ sơ user vận hành

### `study_design`
Chịu trách nhiệm:
- study metadata
- CRF Template
- Page Template
- Visit Definition
- Field Definition
- Validation Rule Definition
- versioning metadata thiết kế

### `study_operations`
Chịu trách nhiệm:
- Site
- StudySite
- Subject
- Enrollment
- Subject status vận hành

### `clinical_capture`
Chịu trách nhiệm:
- VisitInstance
- PageEntry
- FieldEntry
- nhập liệu
- validation runtime
- completion state

### `query_management`
Chịu trách nhiệm:
- manual query
- automation query
- response thread
- close/reopen/resolve lifecycle

### `data_review`
Chịu trách nhiệm:
- review state
- lock field
- lock page
- lock subject
- database lock/freeze/finalization rule

### `audit_compliance`
Chịu trách nhiệm:
- audit trail nghiệp vụ
- immutable change history
- compliance event
- inspection-ready export feed

### `reporting_export`
Chịu trách nhiệm:
- CDISC export
- operational report export
- data package build
- export job lifecycle

### `operational_tracking`
Chịu trách nhiệm:
- dashboard
- KPI
- progress read model
- finalized/locked/query metrics

### `shared_kernel`
Chỉ chứa các thành phần thật sự dùng chung và ổn định:
- base value objects kỹ thuật
- typed ids
- Result/Error primitives
- domain event abstractions
- audit metadata base types

Không được biến thành nơi chứa code dùng chung tùy tiện.

---

## 4) Quy tắc về dependency

### 4.1. Quy tắc import
- Một context **không import trực tiếp domain model nội bộ** của context khác.
- Chỉ được phụ thuộc qua:
  - contract,
  - DTO/query model,
  - published event,
  - anti-corruption adapter.

### 4.2. Quy tắc persistence
- Một context không được viết trực tiếp vào bảng aggregate của context khác.
- Nếu dùng chung một database vật lý, vẫn phải coi schema/table ownership là theo context.
- Mỗi bảng phải có owner context rõ ràng.

### 4.3. Cross-context workflow
Ví dụ hợp lệ:
- `study_design` publish `StudyVersionReleased`
- `clinical_capture` subscribe để mở dữ liệu nhập theo version

Ví dụ không hợp lệ:
- `clinical_capture` cập nhật trực tiếp bảng template của `study_design`

---

## 5) Quy tắc modeling

### 5.1. Entity / Aggregate
- Chỉ tạo aggregate khi có boundary nhất quán thật sự.
- Không biến mọi entity thành aggregate root.
- Aggregate phải bảo vệ invariant quan trọng.

### 5.2. Value Object
Ưu tiên value object cho:
- subject code
- visit code
- page code
- field code
- query status
- lock scope
- audit reason

### 5.3. Domain Service
Dùng domain service khi rule:
- liên quan nhiều aggregate,
- không thuộc tự nhiên vào một entity/value object,
- không chỉ là wrapper gọi repo.

### 5.4. Application Service
Application service:
- điều phối use case,
- mở transaction,
- gọi repo,
- publish event,
- gọi policy/check.

Không nhét nghiệp vụ cốt lõi vào application service.

---

## 6) Quy tắc cho audit và compliance

- Mọi thay đổi có ý nghĩa nghiệp vụ trên dữ liệu lâm sàng phải sinh audit trail.
- Audit trail là append-only.
- Không update/xóa bản ghi audit trail.
- Với thay đổi field entry, phải cố gắng ghi được:
  - actor
  - timestamp
  - aggregate/type
  - before value
  - after value
  - reason
  - source action/use case

Các module không được tự log audit theo cách riêng nếu đã có adapter chuẩn của `audit_compliance`.

---

## 7) Quy tắc đặt tên

### 7.1. Module
- snake_case cho tên thư mục context
- không dùng tên theo menu UI nếu không phản ánh ngôn ngữ nghiệp vụ

### 7.2. Domain types
- PascalCase cho class
- tên phải phản ánh nghiệp vụ, ví dụ:
  - `StudyVersion`
  - `VisitDefinition`
  - `PageEntry`
  - `QueryCase`
  - `DatabaseLock`

### 7.3. Use case
- Đặt theo động từ nghiệp vụ:
  - `CreateSubject`
  - `RecordPageEntry`
  - `RaiseManualQuery`
  - `RespondToQuery`
  - `LockPage`
  - `FinalizeSubject`

### 7.4. Events
- Quá khứ, mô tả fact đã xảy ra:
  - `SubjectEnrolled`
  - `PageEntryRecorded`
  - `QueryOpened`
  - `PageLocked`
  - `DatabaseFrozen`

---

## 8) Quy tắc API và presentation

- Không expose domain entity trực tiếp ra API.
- API request/response dùng DTO riêng.
- Validation chia thành:
  - transport validation
  - application validation
  - domain invariant
- Lỗi domain phải được map nhất quán sang error response.

---

## 9) Quy tắc test

Mỗi feature phải xác định ít nhất các lớp test sau khi phù hợp:
- unit test cho domain rule
- application test cho use case
- integration test cho repository / event / transaction
- contract test nếu context có public contract dùng bởi context khác

Ưu tiên test các nghiệp vụ:
- versioning study design
- data capture invariant
- query lifecycle
- lock hierarchy
- audit trail completeness

---

## 10) Cách thêm feature mới

Khi thêm feature mới, bắt buộc trả lời theo thứ tự:
1. Feature thuộc bounded context nào?
2. Aggregate nào sở hữu invariant chính?
3. Có cần event không?
4. Có ảnh hưởng audit trail không?
5. Có ảnh hưởng read model/reporting không?
6. Có vi phạm boundary hiện tại không?

Bắt buộc dùng skill `feature-scaffold` trước khi code, và dùng `architecture-review` trước merge với feature lớn hoặc thay đổi boundary.

---

## 11) Khi nào phải chạy architecture review

Bắt buộc chạy review nếu có một trong các dấu hiệu sau:
- thêm bounded context mới
- sửa quan hệ giữa các context
- context này cần đọc/ghi dữ liệu của context khác
- thêm shared module mới
- thêm workflow lock/finalization/query phức tạp
- chỉnh sửa schema có ảnh hưởng compliance/audit
- export CDISC mới

---

## 12) Không được làm

- Không tạo thư mục `common/` hoặc `utils/` rồi ném mọi thứ vào đó.
- Không dùng model của ORM như domain model nếu model đó đang ôm persistence concern nặng.
- Không cho `reporting_export` điều khiển ngược rule của core domain.
- Không cho dashboard query viết ngược vào bảng vận hành.
- Không bypass audit trail cho thao tác thay đổi dữ liệu nghiên cứu.
- Không thêm shared abstraction nếu mới chỉ có 1 nơi dùng.

---

## 13) Quy trình pull request

Mọi PR nên có các mục sau:
- Context bị tác động
- Use case được thêm/sửa
- Aggregate/invariant liên quan
- Event mới
- Migration mới
- Ảnh hưởng audit/compliance
- Ảnh hưởng backward compatibility

Nếu PR chạm nhiều context, bắt buộc nêu rõ context map thay đổi ra sao.

---

## 14) Skills bắt buộc đi kèm

Xem tại `.agent/skills/`:

- `architecture-review.md`
- `feature-scaffold.md`
- `bounded-context-checklist.md`
- `coding-standards.md`
- `audit-trail-rules.md`

---

## 15) Cây thư mục chuẩn

```text
apps/
  identity_access/
  user_administration/
  study_design/
  study_operations/
  clinical_capture/
  query_management/
  data_review/
  audit_compliance/
  reporting_export/
  operational_tracking/
  shared_kernel/
```

Chi tiết cây thư mục xem `docs/folder-tree.md`.
