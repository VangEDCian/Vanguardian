# feature-scaffold.md

## Mục đích

Tài liệu này là mẫu bắt buộc trước khi bắt đầu một feature mới trong hệ thống EDC.

Mục tiêu của file này là:

- buộc đội phát triển xác định đúng bounded context trước khi code
- tránh feature đi xuyên nhiều contexts không kiểm soát
- xác định rõ aggregate, invariant, audit trail và contract cross-context
- giảm rủi ro biến feature thành CRUD theo menu UI

---

## Khi nào phải dùng

Bắt buộc dùng cho:

- feature mới
- thay đổi use case hiện có
- thêm command/query mới
- thêm workflow reconcile/query/discrepancy/governance/export
- thêm API mới có ghi dữ liệu
- thêm batch job ảnh hưởng dữ liệu nghiệp vụ
- thêm report/export có logic nghiệp vụ riêng

Không bắt buộc cho:

- đổi text UI đơn giản
- sửa typo
- refactor nội bộ không đổi hành vi
- thay đổi hạ tầng không chạm nghiệp vụ

---

## Cách sử dụng

1. Sao chép file này vào:
   - `docs/features/<yyyy-mm-dd>-<feature-name>.md`
   - hoặc đính kèm trong PR nếu feature nhỏ
2. Điền đầy đủ trước khi bắt đầu code.
3. Nếu feature chạm boundary mới hoặc phá rule dependency, tạo thêm `architecture-review.md`.

---

## Metadata

- **Feature name**:
- **Date**:
- **Author**:
- **Related issue / ticket**:
- **Status**: Draft / Ready / In Progress / Done
- **Priority**:
- **Primary module / bounded context**:

---

## 1. Bài toán nghiệp vụ

Mô tả ngắn gọn:

- feature này phục vụ nghiệp vụ gì
- ai sử dụng
- hành vi mong muốn là gì
- không nên mô tả theo ngôn ngữ UI thuần túy

Ví dụ tốt:

- “Cho phép Data Manager raise manual query trên một field đã nhập của subject”
- “Cho phép lock page sau khi toàn bộ query đã resolved”
- “Cho phép export audit trail của subject theo khoảng thời gian”

---

## 2. Ubiquitous language

Liệt kê các thuật ngữ nghiệp vụ xuất hiện trong feature.

| Term | Meaning in this feature | Owner context |
|---|---|---|
|  |  |  |

Nêu rõ nếu có thuật ngữ dễ nhầm với context khác.

---

## 3. Primary module / bounded context

- **Primary bounded context**:
- **Vì sao feature này thuộc context này**:
- **Invariant chính nằm ở đâu**:

> Nếu không xác định được owner context chính, không bắt đầu code.

---

## 4. Supporting modules / contexts

Liệt kê các context phụ trợ thật sự cần dùng.

| Context | Purpose | Access type |
|---|---|---|
|  |  | read / contract / event / projection |

Không liệt kê context chỉ vì “có liên quan về UI”.

---

## 5. Actor và quyền

| Actor / Role | Action | Permission needed |
|---|---|---|
|  |  |  |

Nêu rõ:

- ai được thực hiện
- ai không được thực hiện
- có kiểm tra site/study ownership không
- có cần phân quyền theo subject/site/study không

---

## 6. Use case summary

### 6.1 Command(s)

Liệt kê command chính.

| Command | Description | Owner context |
|---|---|---|
|  |  |  |

### 6.2 Query(s)

Liệt kê query/read model cần thiết.

| Query | Description | Source |
|---|---|---|
|  |  | public API / projection / reporting model |

---

## 7. Aggregate và invariant

### 7.1 Aggregate(s) touched

| Aggregate | Action | Why needed |
|---|---|---|
|  |  |  |

### 7.2 Invariant(s)

Liệt kê các rule bắt buộc phải giữ.

Ví dụ:

- không raise query/discrepancy trên field không tồn tại
- không sửa page entry khi page đã locked hoặc finalized theo policy
- không reconcile/close discrepancy nếu trạng thái hiện tại không hợp lệ
- không export dữ liệu vượt quá policy do governance cho phép

---

## 8. Luồng nghiệp vụ

Mô tả happy path ngắn gọn theo thứ tự bước.

1.
2.
3.

### 8.1 Alternate flows / edge cases

- trường hợp thiếu permission
- đối tượng không tồn tại
- dữ liệu đang locked
- version mismatch
- duplicated request
- trạng thái không hợp lệ

---

## 9. Cross-context interaction

### 9.1 Contract được dùng

| Source context | Contract / API | Purpose |
|---|---|---|
|  |  |  |

### 9.2 Event được consume

| Event | Producer | Why needed |
|---|---|---|
|  |  |  |

### 9.3 Event được emit

| Event | Consumers expected | Notes |
|---|---|---|
|  |  |  |

### 9.4 Có cần `architecture-review.md` không?

- [ ] Có
- [ ] Không

Nếu không, giải thích ngắn gọn tại sao feature này vẫn nằm gọn trong boundary hiện tại và không tạo dependency mới giữa các module.

---

## 10. Audit trail

Mục này là bắt buộc nếu feature có thay đổi dữ liệu nghiệp vụ.

- **Audit trail required**: Yes / No
- **Why**:
- **Actor**:
- **Action name**:
- **Aggregate / entity target**:
- **Before value needed**: Yes / No
- **After value needed**: Yes / No
- **Reason required**: Yes / No
- **Comment / free-text required**: Yes / No

Ví dụ:

- `ManualQueryRaised`
- `DiscrepancyResolved`
- `FieldEntryCorrected`
- `DatasetExportAuthorized`

---

## 11. Compliance / data protection impact

Đánh giá xem feature có chạm các điểm sau không:

- [ ] dữ liệu cá nhân
- [ ] dữ liệu nghiên cứu lâm sàng
- [ ] audit trail / audit export
- [ ] reconcile / query / discrepancy
- [ ] subject lifecycle
- [ ] exporting / data package ra ngoài hệ thống
- [ ] retention / disposition policy
- [ ] masking / disclosure / access restriction
- [ ] governance approval hoặc policy decision

Nếu có, mô tả ngắn gọn:

- dữ liệu nào
- ai được xem
- ai được sửa
- có cần masking hoặc download control không

---

## 12. Persistence impact

| Table / Projection / Model | Change type | Owner context |
|---|---|---|
|  | new / update / no change |  |

### 12.1 Migration needed

- [ ] Yes
- [ ] No

### 12.2 Projection/backfill needed

- [ ] Yes
- [ ] No

### 12.3 Ownership check

Xác nhận feature này không ghi trực tiếp vào bảng private của context khác.

- [ ] Confirmed

---

## 13. API / presentation impact

| Adapter | Action | Notes |
|---|---|---|
| REST API |  |  |
| Admin |  |  |
| Internal CLI / Job |  |  |
| Message consumer |  |  |

Rule:

- không expose domain entity trực tiếp
- request/response dùng DTO
- transport validation không thay thế domain invariant

---

## 14. Error cases

Liệt kê lỗi có chủ đích cần xử lý.

| Error case | Level | Expected outcome |
|---|---|---|
|  | domain / app / transport / infra |  |

Ví dụ:

- invalid status transition
- page locked
- missing subject
- stale version
- permission denied

---

## 15. Test plan tối thiểu

### Unit tests

- [ ] domain rule
- [ ] value object
- [ ] state transition

### Application tests

- [ ] command handler / use case
- [ ] permission flow
- [ ] transaction boundary

### Integration tests

- [ ] repository
- [ ] public contract
- [ ] event publish/consume
- [ ] audit trail persistence

### Regression tests

- [ ] existing workflow unaffected
- [ ] dashboard/projection unaffected
- [ ] reconcile/governance/export rules unaffected

---

## 16. Done criteria

Feature chỉ được coi là hoàn thành khi:

- [ ] owner context rõ ràng
- [ ] invariant đã được mô tả
- [ ] cross-context interaction rõ ràng
- [ ] audit trail được xử lý đúng
- [ ] permission rules được xác định
- [ ] migration/projection impact đã đánh giá
- [ ] test tối thiểu đã được liệt kê
- [ ] không có import chéo domain trái rule

---

## 17. Gợi ý đánh giá nhanh trước khi code

### Nếu câu trả lời là “không rõ”, dừng lại và review lại thiết kế

- Feature này thuộc context nào?
- Rule cốt lõi nằm ở aggregate nào?
- Có đang dùng UI menu để quyết định boundary không?
- Có đang muốn import thẳng domain của context khác không?
- Có đang định sửa bảng của context khác không?
- Có thao tác nào cần audit mà chưa mô tả không?
- Có trạng thái nào cần lifecycle rõ ràng không?

---

## 18. Ví dụ điền mẫu ngắn

### Ví dụ: Raise Manual Query

- **Primary bounded context**: `reconcile`
- **Supporting contexts**:
  - `datacapture` qua read contract để xác nhận `PageEntry` / `FieldEntry` tồn tại
  - `identity` để xác định actor và permission
- **Aggregate**: `QueryCase`
- **Invariant**:
  - không raise query nếu field path không tồn tại
  - không raise query nếu page đã final lock và policy hiện tại không cho phép query mới
- **Event emitted**:
  - `ManualQueryRaised`
- **Audit trail required**: Yes
- **Architecture review required**: No, nếu chỉ dùng public contract đã có

### Ví dụ: Export Subject Dataset

- **Primary bounded context**: `exporting`
- **Supporting contexts**:
  - `governance` để kiểm tra export authorization, masking/disclosure policy
  - `study` để xác nhận subject thuộc study scope được yêu cầu
  - `audit` để ghi audit trail cho hành vi export hoặc approval decision
- **Aggregate**: `ExportJob`
- **Invariant**:
  - không export nếu governance policy chưa cho phép
  - không export vượt study scope hoặc actor scope đã được cấp quyền
  - dữ liệu phải được masking nếu policy yêu cầu
- **Event emitted**:
  - `DatasetExportRequested`
  - `DatasetExportCompleted`
- **Audit trail required**: Yes
