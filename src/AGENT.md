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

## 2) Top-level modules chính

Các top-level modules dưới đây là **module triển khai cấp cao** cho modular monolith của hệ thống EDC.

Chúng không đồng nghĩa với việc được phép dùng chung domain model nội bộ. Mỗi module vẫn phải giữ boundary rõ ràng, ownership rõ ràng, và tuân thủ quy tắc dependency của tài liệu này.

- `identity`
- `study`
- `crf`
- `datacapture`
- `reconcile`
- `audit`
- `governance`
- `exporting`
- `dashboard`
- `core`

### Ghi chú quan trọng

- Đây là **module triển khai**, không phải lời mời gọi gom mọi thứ “liên quan” vào cùng một chỗ.
- Bên trong mỗi module có thể còn các sub-boundary hoặc subdomain nhỏ hơn.
- Việc chọn ít module top-level hơn nhằm giúp team dễ triển khai hơn, không làm mất đi yêu cầu tách boundary.
- `core` không phải là trung tâm nghiệp vụ. `core` chỉ là nơi chứa primitive và abstraction thật sự ổn định dùng chung.

---

## 3) Ý nghĩa từng module

### `identity`

Chịu trách nhiệm:

- login/logout
- credential
- session/token
- password policy
- authorization runtime check
- user administration
- role assignment
- site/study membership
- quản trị hồ sơ user vận hành

Không được biến thành nơi chứa business rule của study, CRF, query, hoặc review workflow.

### `study`

Chịu trách nhiệm:

- Study
- Site
- StudySite
- Subject
- Enrollment
- Subject status vận hành
- các quan hệ vận hành giữa subject, site và study

Không chứa CRF template, page template, field definition hay query lifecycle.

### `crf`

Chịu trách nhiệm:

- CRF Template
- Page Template
- Visit Definition
- Field Definition
- Validation Rule Definition
- versioning metadata thiết kế

Module này sở hữu ngôn ngữ “phải thu thập dữ liệu gì”, không sở hữu dữ liệu runtime đã được nhập.

### `datacapture`

Chịu trách nhiệm:

- VisitInstance
- PageEntry
- FieldEntry
- nhập liệu
- validation runtime
- completion state
- data entry workflow

Module này sở hữu ngôn ngữ “đã thu thập dữ liệu gì” ở runtime.

### `reconcile`

Chịu trách nhiệm:

- manual query
- automation query
- response thread
- discrepancy resolution
- close/reopen/resolve lifecycle
- readiness check trước lock/finalize khi liên quan dữ liệu chưa sạch hoặc còn nghi vấn

`reconcile` sở hữu workflow làm sạch, hòa giải và xử lý dữ liệu nghi vấn. Không được biến thành nơi chứa nhập liệu gốc, audit trail, permission runtime, hay export logic.

### `audit`

Chịu trách nhiệm:

- audit trail nghiệp vụ
- immutable change history
- compliance event
- inspection-ready trace/feed

`audit` chỉ sở hữu lịch sử thay đổi nghiệp vụ bất biến phục vụ traceability và compliance. Không dùng `audit` như nơi chứa debug log, application log, system log hoặc observability metrics.

### `governance`

Chịu trách nhiệm:

- data access policy
- export authorization policy
- masking/disclosure rule
- retention/disposition policy
- dataset usage / release approval policy
- các policy kiểm soát quyền sử dụng và phát hành dữ liệu

`governance` là nơi sở hữu policy về việc dữ liệu có được xem, sử dụng, che giấu, giữ lại hay phát hành hay không. Không được biến `governance` thành bucket cho mọi loại validation hoặc business rule chung chung.

### `exporting`

Chịu trách nhiệm:

- CDISC export
- operational report export
- audit export package
- data package build
- export job lifecycle

`exporting` chỉ thực hiện build và phát hành output theo contract đã được cho phép. Không điều khiển ngược rule của core domain.

### `dashboard`

Chịu trách nhiệm:

- dashboard
- KPI
- progress read model
- finalized/locked/query metrics
- projection phục vụ theo dõi vận hành

`dashboard` là read-side phục vụ quan sát nghiệp vụ. Không được ghi ngược vào bảng vận hành để thay đổi state nghiệp vụ.

### `core`

Chỉ chứa các thành phần thật sự dùng chung và ổn định:

- base value objects kỹ thuật
- typed ids
- Result/Error primitives
- domain event abstractions
- audit metadata base types
- technical primitives ổn định được nhiều module dùng chung

`core` không phải là nơi đặt domain nghiệp vụ dùng chung. Không được đưa vào `core` các aggregate, entity hoặc rule nghiệp vụ như Subject, Visit, Query, LockPolicy, CRF, StudyStatus hoặc các khái niệm có nghĩa khác nhau giữa các module.

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
- `dependency-rules-edc.md`

---

## 15) Cây thư mục chuẩn

```text
apps/
  identity/
  study/
  crf/
  datacapture/
  reconcile/
  audit/
  governance/
  exporting/
  dashboard/
  core/
```

Chi tiết cây thư mục xem `docs/folder-tree.md`.
