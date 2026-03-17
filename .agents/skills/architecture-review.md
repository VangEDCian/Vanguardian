# architecture-review.md

## Mục đích

Tài liệu này là mẫu bắt buộc khi có thay đổi ảnh hưởng đến kiến trúc, boundary, dependency, persistence ownership hoặc compliance flow của hệ thống EDC.

Mọi thay đổi thuộc một trong các trường hợp sau phải có `architecture-review.md` đi kèm trong PR hoặc ADR tương ứng:

- thêm bounded context mới
- gộp hoặc tách bounded context
- thêm dependency mới giữa hai contexts
- thêm shared abstraction vào `shared_kernel`
- cho phép đọc chéo dữ liệu giữa contexts
- thay đổi ownership của bảng hoặc schema
- thay đổi flow audit trail, query lifecycle, lock/finalization
- thêm export/reporting pipeline dùng dữ liệu từ nhiều contexts
- thêm cơ chế async/event integration mới
- thay đổi public contract của context đang được context khác dùng

---

## Cách sử dụng

1. Sao chép mẫu này vào:
   - `docs/architecture-review/<yyyy-mm-dd>-<slug>.md`
   - hoặc đính kèm trong PR nếu thay đổi nhỏ nhưng vẫn chạm boundary
2. Điền đầy đủ tất cả các mục bắt buộc.
3. Không merge nếu chưa xác định rõ:
   - owner context
   - source/target dependency
   - audit/compliance impact
   - rollback/refactor direction

---

## Metadata

- **Title**:
- **Date**:
- **Author**:
- **Related PR / Issue**:
- **Status**: Proposed / Accepted / Rejected / Superseded
- **Decision Type**: New dependency / Boundary change / Persistence change / Event integration / Compliance change / Other

---

## 1. Bối cảnh

Mô tả ngắn gọn vấn đề đang gặp phải hoặc nhu cầu mới.

Gợi ý viết:
- feature nào đang cần
- tại sao thiết kế hiện tại không còn đủ
- giới hạn hiện tại nằm ở đâu
- áp lực đến từ nghiệp vụ, compliance, hiệu năng hay tổ chức

---

## 2. Hiện trạng

### 2.1 Context hiện tại bị tác động
- Source context(s):
- Target context(s):
- Shared components liên quan:

### 2.2 Luồng hiện tại
Mô tả cách hệ thống đang vận hành trước thay đổi này.

### 2.3 Invariant / rule hiện tại
Liệt kê các invariant hoặc rule đang được giữ bởi kiến trúc hiện tại.

Ví dụ:
- `clinical_capture` sở hữu `PageEntry`
- `query_management` không được update trực tiếp `PageEntry`
- `audit_compliance` là append-only
- `data_review` sở hữu finalization/lock decision

---

## 3. Vấn đề cần giải quyết

Mô tả chính xác điều gì đang bị thiếu hoặc gây cản trở.

### 3.1 Tín hiệu cho thấy cần review kiến trúc
Đánh dấu các mục áp dụng:

- [ ] Context A cần dùng trực tiếp dữ liệu hoặc rule của Context B
- [ ] Cần thêm public contract mới
- [ ] Cần thêm read model / projection dùng chung
- [ ] Cần thay đổi ownership bảng
- [ ] Cần thêm event mới
- [ ] Cần nới rule dependency
- [ ] Cần chia lại boundary
- [ ] Cần hỗ trợ audit/compliance mới
- [ ] Cần thêm export/reporting path mới

### 3.2 Nếu không thay đổi
Điều gì sẽ xảy ra nếu giữ nguyên kiến trúc hiện tại?

---

## 4. Các phương án đã xem xét

Mỗi phương án nên nêu:
- mô tả
- ưu điểm
- nhược điểm
- rủi ro compliance / audit / coupling
- lý do không chọn hoặc điều kiện để chọn

### Option A — Giữ nguyên kiến trúc, chỉ xử lý ở application layer
- Mô tả:
- Ưu điểm:
- Nhược điểm:
- Kết luận:

### Option B — Thêm public contract / facade
- Mô tả:
- Ưu điểm:
- Nhược điểm:
- Kết luận:

### Option C — Dùng domain event / projection
- Mô tả:
- Ưu điểm:
- Nhược điểm:
- Kết luận:

### Option D — Tách / gộp / đổi ownership context
- Mô tả:
- Ưu điểm:
- Nhược điểm:
- Kết luận:

---

## 5. Quyết định được chọn

### 5.1 Decision summary
Viết ngắn gọn quyết định cuối cùng.

### 5.2 Kiểu thay đổi
Đánh dấu các mục áp dụng:

- [ ] Thêm dependency qua `public.py`
- [ ] Thêm gateway interface
- [ ] Thêm published read model
- [ ] Thêm domain event
- [ ] Thêm integration event nội bộ
- [ ] Thay đổi ownership bảng/schema
- [ ] Tách bounded context
- [ ] Gộp bounded context
- [ ] Bổ sung rule vào shared kernel
- [ ] Khác

### 5.3 Owner sau thay đổi
| Thành phần | Owner context |
|---|---|
|  |  |

---

## 6. Ảnh hưởng đến dependency

### 6.1 Dependency mới
| Source | Target | Type | Allowed via | Notes |
|---|---|---|---|---|
|  |  | sync / async / read-only | public.py / event / projection / ACL |  |

### 6.2 Dependency bị cấm vẫn giữ nguyên
Liệt kê rõ các thứ vẫn không được phép sau thay đổi.

Ví dụ:
- `clinical_capture.domain` không import `study_design.domain`
- `query_management` không update trực tiếp bảng `clinical_capture_*`
- `reporting_export` không điều khiển ngược core domain

---

## 7. Ảnh hưởng đến persistence ownership

### 7.1 Bảng / schema / projection bị tác động
| Name | Current owner | New owner | Change type | Notes |
|---|---|---|---|---|
|  |  |  | unchanged / transferred / new projection |  |

### 7.2 Rule ownership
- Context nào được write?
- Context nào chỉ được read?
- Read bằng cơ chế gì?
- Có direct DB join không?
- Nếu có projection/view dùng chung, ai publish? ai consume?

---

## 8. Ảnh hưởng đến audit, compliance và bảo mật dữ liệu

Mục này là bắt buộc cho mọi thay đổi liên quan dữ liệu nghiên cứu, subject, query, review, export.

### 8.1 Audit trail impact
- Thay đổi này có tạo thêm audit event không?
- Có làm mất before/after value không?
- Có thay đổi actor/source action không?
- Có khả năng bypass audit trail không?

### 8.2 Compliance impact
- Có ảnh hưởng inspection readiness không?
- Có thay đổi retention / delete / export / traceability không?
- Có dùng dữ liệu cá nhân mới không?
- Có cần cập nhật data protection controls không?

### 8.3 Security / access impact
- Có permission mới không?
- Có exposure mới qua API / export / reporting không?
- Có read path mới tới dữ liệu nhạy cảm không?

---

## 9. Ảnh hưởng đến ubiquitous language

### 9.1 Thuật ngữ mới
| Term | Context owner | Meaning | Notes |
|---|---|---|---|
|  |  |  |  |

### 9.2 Thuật ngữ có nguy cơ chồng lấn
Nêu rõ các từ có thể bị dùng sai giữa các contexts.

Ví dụ:
- `VisitDefinition` vs `VisitInstance`
- `QueryStatus` vs `ReviewStatus`
- `Freeze` vs `Lock` vs `Finalize`

---

## 10. Public contract được thêm hoặc sửa

### 10.1 Contract mới
```python
# ví dụ minh họa
class SubjectRegistry(Protocol):
    def exists(self, subject_id: SubjectId) -> bool: ...
    def is_active_for_study(self, subject_id: SubjectId, study_id: StudyId) -> bool: ...
```

### 10.2 Contract thay đổi
- Breaking change?
- Consumer nào bị ảnh hưởng?
- Kế hoạch migration?

---

## 11. Boundary exception

Điền mục này nếu có bất kỳ ngoại lệ nào phá boundary chuẩn.

### Boundary exception 1
- **Source context**:
- **Target context**:
- **Reason**:
- **Why existing public API is insufficient**:
- **Temporary or permanent**:
- **Risk introduced**:
- **Removal/refactor plan**:
- **Expiry date or review date**:

Có thể lặp lại mục này nếu có nhiều exception.

---

## 12. Kế hoạch triển khai

### 12.1 Bước thực hiện
1.
2.
3.

### 12.2 Migration / rollout
- cần migration dữ liệu không?
- cần backfill projection không?
- có cần chạy job một lần không?
- có cần feature flag không?

### 12.3 Test bắt buộc
- [ ] unit tests cho rule mới
- [ ] application tests cho use case
- [ ] integration tests cho dependency mới
- [ ] contract tests cho public API mới
- [ ] audit trail tests
- [ ] permission / security tests
- [ ] export / reporting regression tests

---

## 13. Rủi ro và biện pháp giảm thiểu

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
|  |  |  |  |

---

## 14. Tiêu chí chấp nhận review

Chỉ được coi là review đạt khi:

- [ ] owner context rõ ràng
- [ ] dependency mới được mô tả rõ
- [ ] persistence ownership rõ
- [ ] audit/compliance impact đã đánh giá
- [ ] không có import chéo domain trái rule
- [ ] đã nêu phương án rollback/refactor
- [ ] đã xác định test cần bổ sung

---

## 15. Quyết định cuối cùng

- **Approved by**:
- **Approved on**:
- **Conditions / follow-ups**:

---

## 16. Hành động tiếp theo

| Action | Owner | Due date |
|---|---|---|
|  |  |  |
