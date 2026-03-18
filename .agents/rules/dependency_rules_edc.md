# Dependency Rules cho EDC Django

## 1. Mục tiêu

Các rule này nhằm bảo đảm:

- bounded context không bị xuyên thủng bởi import chéo
- domain model không bị dùng chung tùy tiện
- cross-context integration đi qua contract rõ ràng
- codebase giữ được khả năng mở rộng theo modular monolith

---

## 2. Nguyên tắc gốc

### Rule G1 — Bounded context là ranh giới ownership

Mỗi bounded context sở hữu:

- ngôn ngữ nghiệp vụ riêng
- aggregate riêng
- invariant riêng
- persistence riêng
- application service riêng

Không context nào được coi domain nội bộ của context khác là public API mặc định.

### Rule G2 — Không chia sẻ internal model

Entity, aggregate, value object, repository, domain service bên trong một context là **private**.

Chúng không được dùng trực tiếp từ context khác.

### Rule G3 — Cross-context chỉ qua contract

Nếu context A cần dùng năng lực của context B, chỉ được đi qua một trong các cơ chế sau:

- `public.py`
- application facade
- DTO / read model
- gateway interface
- domain event
- anti-corruption layer

Không được import thẳng `domain/`, `models.py`, `repositories.py` nội bộ của context khác.

---

## 3. Cấu trúc package chuẩn

```sh
apps/
  identity/
    apps.py
    public.py
    domain/
    application/
    infrastructure/
    presentation/
  study/
    apps.py
    public.py
    domain/
    application/
    infrastructure/
    presentation/
  crf/
    apps.py
    public.py
    domain/
    application/
    infrastructure/
    presentation/
  datacapture/
    apps.py
    public.py
    domain/
    application/
    infrastructure/
    presentation/
  reconcile/
    apps.py
    public.py
    domain/
    application/
    infrastructure/
    presentation/
```

---

## 4. Import Rules

### Rule I1 — `domain/` không được import `domain/` của context khác

**Cấm**

```python
from apps.crf.domain.entities import PageTemplate
from apps.reconcile.domain.models import QueryCase
```

**Cho phép**

```python
from apps.core.domain.ids import StudyId, SubjectId, PageEntryId
```

**Giải thích**

Domain phải giữ invariant của chính nó. Nếu domain import domain khác, model sẽ bị coupling ngầm.

### Rule I2 — `application/` được gọi sang context khác chỉ qua `public.py`

**Đúng**

```python
from apps.study.public import StudySubjectQueryService
```

**Sai**

```python
from apps.study.application.subject_queries import StudySubjectQueryService
from apps.study.domain.subject import Subject
```

### Rule I3 — `infrastructure/` có thể tích hợp kỹ thuật, nhưng không được làm lộ internal domain xuyên context

Ví dụ `datacapture.infrastructure` có thể gọi DB, cache, broker, nhưng không được trở thành đường vòng để sửa private state của `crf` hoặc `study`.

### Rule I4 — `presentation/` không được chứa business rule xuyên context

Controller/API/View có thể orchestration mức nhẹ, nhưng không được:

- quyết định invariant
- cập nhật nhiều context trực tiếp bằng logic tùy tiện
- bypass application service

---

## 5. Public API Rules

### Rule P1 — Mỗi context phải có `public.py`

`public.py` là cổng vào chính thức cho context khác.

Ví dụ:

```python
# apps/study/public.py

from .application.subject_queries import StudySubjectQueryService
from .application.subject_commands import StudySubjectCommandService

__all__ = [
    "StudySubjectQueryService",
    "StudySubjectCommandService",
]
```

### Rule P2 — Chỉ expose use case hoặc contract ổn định

`public.py` chỉ được export:

- application service
- command/query handler facade
- DTO/query object
- interface contract

Không export:

- aggregate nội bộ
- ORM model
- repository implementation

### Rule P3 — Public API phải semantic, không phải technical shortcut

**Tốt**

- `SubjectRegistry`
- `StudyTemplateReader`
- `RaiseManualQuery`
- `LockPageCommand`

**Kém**

- `SubjectModel`
- `PageEntryRepositoryImpl`
- `TemplateORMAccessor`

---

## 6. Shared Kernel Rules

### Rule S1 — Shared kernel phải cực nhỏ

Chỉ được đặt trong `core` các thành phần sau:

- ID types: `StudyId`, `SiteId`, `SubjectId`, `UserId`
- domain event base class
- result/error primitives
- enum ổn định, dùng toàn hệ thống
- clock / correlation metadata abstractions
- audit metadata primitives dùng chung nếu thật sự ổn định

### Rule S2 — Không đặt aggregate/domain nghiệp vụ vào shared kernel

**Cấm**

- `Subject`
- `Visit`
- `PageTemplate`
- `QueryCase`
- `FieldLock`

Nếu một khái niệm có hành vi nghiệp vụ riêng, nó phải thuộc một bounded context cụ thể.

### Rule S3 — Shared kernel chỉ chứa khái niệm có nghĩa nhất quán toàn hệ thống

Nếu từ đó có nghĩa khác nhau theo context, không được đưa vào shared kernel.

Ví dụ:

- `VisitDefinition` và `VisitInstance` không được gom thành `Visit`

---

## 7. Data Ownership Rules

### Rule D1 — Mỗi bảng/private persistence có owner duy nhất

Mỗi bảng hoặc aggregate store phải có một context sở hữu.

Ví dụ:

- `crf_*` do `crf` sở hữu
- `datacapture_*` do `datacapture` sở hữu
- `reconcile_*` do `reconcile` sở hữu

### Rule D2 — Không context nào được update bảng private của context khác

**Cấm**

`reconcile` update trực tiếp bảng page entry để đóng discrepancy/query flag.

**Đúng**

- gọi public API của `datacapture`
- hoặc phát event
- hoặc materialize read model riêng

### Rule D3 — Đọc chéo được phép theo mức kiểm soát

Có 3 mức đọc:

#### Mức A — Qua public query service

Ưu tiên nhất.

#### Mức B — Qua read model/projection

Dùng cho dashboard, reporting, tracking.

#### Mức C — Đọc trực tiếp DB view/projection được publish

Chỉ khi đã được review và ghi nhận architecture decision.

Không được đọc trực tiếp bảng private theo kiểu “tiện thì join”.

---

## 8. Cross-Context Communication Rules

### Rule C1 — Đồng bộ qua application facade khi cần quyết định tức thời

Ví dụ `datacapture` cần kiểm tra subject còn active trong study không:

```python
class StudySubjectRegistry(Protocol):
    def subject_exists(self, subject_id: SubjectId) -> bool: ...
    def subject_belongs_to_study(self, subject_id: SubjectId, study_id: StudyId) -> bool: ...
```

### Rule C2 — Bất đồng bộ qua domain event khi không cần transaction chung

Ví dụ:

- `PageFinalized`
- `ManualQueryRaised`
- `SubjectEnrolled`
- `DatabaseLocked`

Dashboard, audit, exporting và governance projections nên tiêu thụ event/projection thay vì bám write model.

### Rule C3 — Không truyền aggregate xuyên context

**Cấm**

```python
capture_service.record(subject: Subject, template: PageTemplate)
```

**Đúng**

```python
capture_service.record(
    subject_id=subject_id,
    page_template_id=page_template_id,
    page_template_version=version,
)
```

Hoặc truyền DTO/snapshot:

```python
@dataclass(frozen=True)
class PageTemplateSnapshot:
    page_template_id: str
    version: int
    fields: list[FieldSchemaSnapshot]
```

---

## 9. Domain Rules

### Rule R1 — Domain chỉ xử lý invariant của chính context đó

Ví dụ:

- `datacapture.domain` xử lý field entry, completion, validation result tại thời điểm capture
- `reconcile.domain` xử lý query/discrepancy lifecycle
- `governance.domain` xử lý policy decision về access/export/masking/retention

Không domain nào ôm logic nghiệp vụ của context khác.

### Rule R2 — Nếu rule cần dữ liệu bên ngoài, domain nhận fact đã được chuẩn hóa

Không kéo external dependency trực tiếp vào domain.

**Kém**
Domain gọi ORM/query context khác.

**Tốt**
Application service lấy dữ liệu cần thiết, chuyển vào domain dưới dạng:

- primitive
- DTO
- snapshot
- policy input

### Rule R3 — Một aggregate không chứa lifecycle của aggregate context khác

Ví dụ `PageEntry` không nên mang toàn bộ lifecycle của `QueryCase` hoặc `DatabaseLock`.

Chỉ giữ reference hoặc derived state tối thiểu nếu cần.

---

## 10. Django-specific Rules

### Rule J1 — Mỗi bounded context có thể là một Django app, nhưng không bắt buộc mọi package con đều là Django app

Ví dụ:

- context là Django app
- `domain/application/infrastructure` là package nội bộ

Điều quan trọng là boundary, không phải số lượng app Django.

### Rule J2 — `models.py` không đồng nghĩa với domain model

Nếu dùng Django ORM, `models.py` là persistence model. Không được mặc định xem ORM model là toàn bộ domain.

Khuyến nghị:

- ORM model ở `infrastructure/persistence/models.py`
- domain entity/value object ở `domain/`

Nếu team chưa tách sâu đến mức đó, vẫn phải ghi rõ:

- model nào là persistence concern
- invariant nào nằm ở application/domain layer

### Rule J3 — Admin site không được là đường bypass domain rule

Django admin chỉ dùng cho:

- vận hành kỹ thuật có kiểm soát
- reference data đơn giản

Không dùng admin để thao tác những luồng cần audit/invariant nghiêm ngặt như:

- authorize dataset export
- close discrepancy/query
- modify clinical entry có kiểm soát
- thay đổi governance policy decision có audit bắt buộc

### Rule J4 — Migration ownership theo context

Migration của bảng context nào phải nằm trong app/context đó. Không tạo migration chạm bảng context khác nếu không có architecture review.

---

## 11. Review Rules

### Rule A1 — Mọi dependency mới giữa 2 contexts phải được review

Bất kỳ dependency mới nào sau đây phải ghi vào `architecture-review.md`:

- import public API mới
- read model mới dùng chéo context
- core abstractions mở rộng
- event integration mới
- DB projection/view dùng chung mới

### Rule A2 — Nếu phải phá boundary, phải ghi rõ lý do và thời hạn

Cấu trúc tối thiểu:

```md
## Boundary exception
- Source context:
- Target context:
- Reason:
- Why existing public API is insufficient:
- Temporary or permanent:
- Removal/refactor plan:
```

### Rule A3 — Không merge feature nếu chưa xác định owner context

Mỗi feature phải khai báo:

- owner context chính
- context phụ thuộc
- contract cross-context sử dụng

---

## 12. Feature Scaffold Rules

Mỗi feature mới phải trả lời tối thiểu các câu hỏi sau:

```md
# Feature Scaffold

## Feature name
## Primary bounded context
## Supporting contexts
## Ubiquitous language terms
## Command(s)
## Query(s)
## Aggregate(s) touched
## Domain events emitted
## Audit trail required?
## Cross-context contracts used
## New tables / schema changes
## Risks to existing boundary
```

---

## 13. Ví dụ cụ thể

### Ví dụ 1 — Datacapture cần biết template

**Sai**

```python
from apps.crf.domain.page_template import PageTemplate
```

**Đúng**

```python
from apps.crf.public import CrfTemplateReader
```

Hoặc:

```python
template_snapshot = crf_template_reader.get_page_template_snapshot(
    page_template_id=page_template_id,
    version=version,
)
```

`datacapture` chỉ dùng snapshot để record entry.

### Ví dụ 2 — Reconcile cần gắn với field entry

**Sai**

`QueryCase` giữ reference ORM trực tiếp đến `FieldEntry` object và sửa trạng thái của nó.

**Đúng**

`QueryCase` chỉ giữ:

- `subject_id`
- `page_entry_id`
- `field_path`
- `query_source`
- `status`

Nếu cần derived status cho UI, build read model hoặc application orchestration.

### Ví dụ 3 — Exporting cần dữ liệu nhiều module

**Sai**
`exporting` join trực tiếp toàn bộ bảng private mỗi khi chạy export.

**Đúng**

- dùng export projection hoặc published query contract
- hỏi `governance` về policy/authorization trước khi phát hành dữ liệu
- ghi audit trail cho hành vi export hoặc approval decision

---

## 14. Rule ngắn gọn để dán vào AGENT.MD

### Allowed

- import từ `core`
- import từ `other_context.public`
- giao tiếp qua DTO / event / facade / gateway
- đọc qua published projection/read model
- mỗi bảng có một owner context

### Forbidden

- import `other_context.domain.*`
- import `other_context.application.*` trực tiếp
- dùng ORM model context khác như domain object của mình
- update bảng private của context khác
- nhét aggregate nghiệp vụ vào `core`
- để Django admin bypass use case quan trọng

---

## 15. AGENT.MD snippet sẵn dùng

```md
## Dependency Rules

1. `domain/` của một bounded context không được import `domain/` của bounded context khác.
2. Cross-context access chỉ được phép qua `public.py`, published DTOs, domain events, hoặc gateway interfaces.
3. Không được dùng trực tiếp ORM model, aggregate, repository nội bộ của context khác.
4. Core chỉ chứa IDs, stable enums, domain-event base classes, result/error primitives, và metadata rất ổn định.
5. Không aggregate nghiệp vụ nào được đặt trong core.
6. Mỗi bảng/private persistence phải có đúng một owner context.
7. Không được update bảng private của context khác.
8. Mọi dependency mới giữa các contexts phải được ghi vào `architecture-review.md`.
9. Mọi feature mới phải khai báo owner context và cross-context contracts trong `feature-scaffold.md`.
10. Django admin không được dùng để bypass các use case có invariant hoặc audit-trail quan trọng.
```

---

## 16. Ghi chú triển khai

Bộ rule này chỉ có giá trị thực nếu được cưỡng chế bằng test hoặc lint. Khuyến nghị bổ sung:

- `architecture-review.md`
- `feature-scaffold.md`
- `import-linter` hoặc architecture tests bằng pytest để chặn import chéo trong CI
