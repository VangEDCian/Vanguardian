# Folder Tree đề xuất

```bash
.
├── AGENT.md
├── docker/
│   └── docker-compose.yml
├── docs/
│   ├── architecture-review.md
│   ├── dependency-rules-edc.md
│   ├── feature-scaffold.md
│   └── folder-tree.md
├── manage.py
├── README.md
├── src/
│   ├── Dockerfile
│   ├── apps/
│   │   ├── identity/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── migrations/
│   │   │   ├── application/
│   │   │   │   ├── commands/
│   │   │   │   ├── dto/
│   │   │   │   ├── queries/
│   │   │   │   └── services/
│   │   │   ├── domain/
│   │   │   │   ├── aggregates/
│   │   │   │   ├── entities/
│   │   │   │   ├── events/
│   │   │   │   ├── policies/
│   │   │   │   ├── repositories/
│   │   │   │   ├── services/
│   │   │   │   └── value_objects/
│   │   │   ├── infrastructure/
│   │   │   │   ├── auth/
│   │   │   │   ├── persistence/
│   │   │   │   │   ├── mappers/
│   │   │   │   │   ├── models/
│   │   │   │   │   └── repositories/
│   │   │   │   └── services/
│   │   │   ├── presentation/
│   │   │   │   ├── admin/
│   │   │   │   ├── api/
│   │   │   │   ├── cli/
│   │   │   │   └── serializers/
│   │   │   └── public.py
│   │   ├── study/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── migrations/
│   │   │   ├── application/
│   │   │   │   ├── commands/
│   │   │   │   ├── dto/
│   │   │   │   ├── queries/
│   │   │   │   └── services/
│   │   │   ├── domain/
│   │   │   │   ├── aggregates/
│   │   │   │   ├── entities/
│   │   │   │   ├── events/
│   │   │   │   ├── policies/
│   │   │   │   ├── repositories/
│   │   │   │   ├── services/
│   │   │   │   └── value_objects/
│   │   │   ├── infrastructure/
│   │   │   │   ├── persistence/
│   │   │   │   │   ├── mappers/
│   │   │   │   │   ├── models/
│   │   │   │   │   └── repositories/
│   │   │   │   └── services/
│   │   │   ├── presentation/
│   │   │   │   ├── admin/
│   │   │   │   ├── api/
│   │   │   │   ├── cli/
│   │   │   │   └── serializers/
│   │   │   └── public.py
│   │   ├── crf/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── migrations/
│   │   │   ├── application/
│   │   │   │   ├── commands/
│   │   │   │   ├── dto/
│   │   │   │   ├── queries/
│   │   │   │   └── services/
│   │   │   ├── domain/
│   │   │   │   ├── aggregates/
│   │   │   │   ├── entities/
│   │   │   │   ├── events/
│   │   │   │   ├── policies/
│   │   │   │   ├── repositories/
│   │   │   │   ├── services/
│   │   │   │   └── value_objects/
│   │   │   ├── infrastructure/
│   │   │   │   ├── persistence/
│   │   │   │   │   ├── mappers/
│   │   │   │   │   ├── models/
│   │   │   │   │   └── repositories/
│   │   │   │   └── services/
│   │   │   ├── presentation/
│   │   │   │   ├── admin/
│   │   │   │   ├── api/
│   │   │   │   ├── cli/
│   │   │   │   └── serializers/
│   │   │   └── public.py
│   │   ├── datacapture/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── migrations/
│   │   │   ├── application/
│   │   │   │   ├── commands/
│   │   │   │   ├── dto/
│   │   │   │   ├── queries/
│   │   │   │   └── services/
│   │   │   ├── domain/
│   │   │   │   ├── aggregates/
│   │   │   │   ├── entities/
│   │   │   │   ├── events/
│   │   │   │   ├── policies/
│   │   │   │   ├── repositories/
│   │   │   │   ├── services/
│   │   │   │   └── value_objects/
│   │   │   ├── infrastructure/
│   │   │   │   ├── persistence/
│   │   │   │   │   ├── mappers/
│   │   │   │   │   ├── models/
│   │   │   │   │   └── repositories/
│   │   │   │   └── services/
│   │   │   ├── presentation/
│   │   │   │   ├── admin/
│   │   │   │   ├── api/
│   │   │   │   ├── cli/
│   │   │   │   └── serializers/
│   │   │   └── public.py
│   │   ├── reconcile/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── migrations/
│   │   │   ├── application/
│   │   │   │   ├── commands/
│   │   │   │   ├── dto/
│   │   │   │   ├── queries/
│   │   │   │   └── services/
│   │   │   ├── domain/
│   │   │   │   ├── aggregates/
│   │   │   │   ├── entities/
│   │   │   │   ├── events/
│   │   │   │   ├── policies/
│   │   │   │   ├── repositories/
│   │   │   │   ├── services/
│   │   │   │   └── value_objects/
│   │   │   ├── infrastructure/
│   │   │   │   ├── persistence/
│   │   │   │   │   ├── mappers/
│   │   │   │   │   ├── models/
│   │   │   │   │   └── repositories/
│   │   │   │   └── services/
│   │   │   ├── presentation/
│   │   │   │   ├── admin/
│   │   │   │   ├── api/
│   │   │   │   ├── cli/
│   │   │   │   └── serializers/
│   │   │   └── public.py
│   │   ├── audit/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── migrations/
│   │   │   ├── application/
│   │   │   │   ├── commands/
│   │   │   │   ├── dto/
│   │   │   │   ├── queries/
│   │   │   │   └── services/
│   │   │   ├── domain/
│   │   │   │   ├── aggregates/
│   │   │   │   ├── entities/
│   │   │   │   ├── events/
│   │   │   │   ├── policies/
│   │   │   │   ├── repositories/
│   │   │   │   ├── services/
│   │   │   │   └── value_objects/
│   │   │   ├── infrastructure/
│   │   │   │   ├── persistence/
│   │   │   │   │   ├── mappers/
│   │   │   │   │   ├── models/
│   │   │   │   │   └── repositories/
│   │   │   │   └── services/
│   │   │   ├── presentation/
│   │   │   │   ├── admin/
│   │   │   │   ├── api/
│   │   │   │   ├── cli/
│   │   │   │   └── serializers/
│   │   │   └── public.py
│   │   ├── governance/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── migrations/
│   │   │   ├── application/
│   │   │   │   ├── commands/
│   │   │   │   ├── dto/
│   │   │   │   ├── queries/
│   │   │   │   └── services/
│   │   │   ├── domain/
│   │   │   │   ├── aggregates/
│   │   │   │   ├── entities/
│   │   │   │   ├── events/
│   │   │   │   ├── policies/
│   │   │   │   ├── repositories/
│   │   │   │   ├── services/
│   │   │   │   └── value_objects/
│   │   │   ├── infrastructure/
│   │   │   │   ├── persistence/
│   │   │   │   │   ├── mappers/
│   │   │   │   │   ├── models/
│   │   │   │   │   └── repositories/
│   │   │   │   └── services/
│   │   │   ├── presentation/
│   │   │   │   ├── admin/
│   │   │   │   ├── api/
│   │   │   │   ├── cli/
│   │   │   │   └── serializers/
│   │   │   └── public.py
│   │   ├── exporting/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── migrations/
│   │   │   ├── application/
│   │   │   │   ├── commands/
│   │   │   │   ├── dto/
│   │   │   │   ├── queries/
│   │   │   │   └── services/
│   │   │   ├── domain/
│   │   │   │   ├── aggregates/
│   │   │   │   ├── entities/
│   │   │   │   ├── events/
│   │   │   │   ├── policies/
│   │   │   │   ├── repositories/
│   │   │   │   ├── services/
│   │   │   │   └── value_objects/
│   │   │   ├── infrastructure/
│   │   │   │   ├── persistence/
│   │   │   │   │   ├── mappers/
│   │   │   │   │   ├── models/
│   │   │   │   │   └── repositories/
│   │   │   │   └── services/
│   │   │   ├── presentation/
│   │   │   │   ├── admin/
│   │   │   │   ├── api/
│   │   │   │   ├── cli/
│   │   │   │   └── serializers/
│   │   │   └── public.py
│   │   ├── dashboard/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── application/
│   │   │   │   ├── dto/
│   │   │   │   ├── queries/
│   │   │   │   └── services/
│   │   │   ├── domain/
│   │   │   │   ├── policies/
│   │   │   │   └── value_objects/
│   │   │   ├── infrastructure/
│   │   │   │   ├── projections/
│   │   │   │   ├── readmodels/
│   │   │   │   └── services/
│   │   │   ├── presentation/
│   │   │   │   ├── api/
│   │   │   │   ├── cli/
│   │   │   │   └── serializers/
│   │   │   └── public.py
│   │   └── core/
│   │       ├── README.md
│   │       ├── __init__.py
│   │       ├── application/
│   │       ├── domain/
│   │       │   ├── errors/
│   │       │   ├── events/
│   │       │   ├── ids/
│   │       │   ├── result/
│   │       │   └── value_objects/
│   │       ├── infrastructure/
│   │       └── presentation/
│   ├── staticfiles/
│   │   ├── images/
│   │   ├── scripts/
│   │   │   ├── audit/
│   │   │   ├── core/
│   │   │   ├── crf/
│   │   │   ├── dashboard/
│   │   │   ├── datacapture/
│   │   │   ├── exporting/
│   │   │   ├── governance/
│   │   │   ├── identity/
│   │   │   ├── reconcile/
│   │   │   └── study/
│   │   └── styles/
│   │       ├── audit/
│   │       ├── core/
│   │       ├── crf/
│   │       ├── dashboard/
│   │       ├── datacapture/
│   │       ├── exporting/
│   │       ├── governance/
│   │       ├── identity/
│   │       ├── reconcile/
│   │       └── study/
│   ├── templates/
│   │   ├── audit/
│   │   ├── core/
│   │   ├── crf/
│   │   ├── dashboard/
│   │   ├── datacapture/
│   │   ├── exporting/
│   │   ├── governance/
│   │   ├── identity/
│   │   ├── reconcile/
│   │   └── study/
│   └── Vanguardian/
│       ├── __init__.py
│       ├── asgi.py
│       ├── settings.py
│       ├── urls.py
│       └── wsgi.py
└── tests/
    ├── integration/
    ├── unit/
    └── architecture/
```

## Ghi chú

- `src/apps/` là nơi chứa các top-level modules theo đúng boundary đã được định nghĩa trong `AGENT.md`.
- Mỗi module có `public.py` để làm public contract cho module khác. Không import trực tiếp `domain/` hoặc `application/` nội bộ của module khác.
- `presentation/` có thể là REST API, Django admin adapter, internal CLI, scheduler entrypoint hoặc message handler.
- `dashboard` thiên về read-side, projection và query model; không phải write domain chính.
- `core` chỉ chứa primitive, ids, result/error, event abstraction và các technical primitives ổn định. Không đặt aggregate nghiệp vụ vào `core`.
- `migrations/` nên nằm trong `infrastructure/persistence/` của chính module sở hữu dữ liệu để giữ ownership rõ ràng.
- `src/templates/` là nơi chứa toàn bộ Django templates dùng chung cho toàn hệ thống, và được phân chia theo từng module context để tránh trộn view/template giữa các boundary.
- `src/staticfiles/` là nơi chứa static assets phục vụ phát triển và render giao diện.
- Bên trong `src/staticfiles/` phải chia thành `styles/`, `scripts/` và `images/` để tách rõ CSS, JavaScript và image assets.
- Bên trong `styles/` và `scripts/`, tiếp tục phân chia theo từng module context để giữ ownership rõ ràng, ví dụ `src/staticfiles/styles/reconcile/...` hoặc `src/staticfiles/scripts/reconcile/...`.
- Khi xây dựng template, ưu tiên đặt template theo namespace module tương ứng, và toàn bộ CSS/JS phải tham chiếu từ `staticfiles/` thay vì viết inline trực tiếp trong template.

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
staticfiles/
  images/
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
  scripts/
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
  styles/
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
templates/
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

### Ghi chú thêm về Django templates và staticfiles

- `templates/` là thư mục tập trung cho Django templates của toàn dự án, nhưng vẫn phải phân namespace theo module để không phá boundary.
- `staticfiles/` là thư mục tập trung cho static assets phục vụ phát triển, render UI và adapter presentation; không dùng nó để che mờ ownership giữa các module.
- `staticfiles/` phải tách rõ thành ba nhóm: `styles/`, `scripts/`, và `images/`.
- `styles/` chỉ chứa CSS hoặc style assets cùng nhóm trách nhiệm hiển thị.
- `scripts/` chỉ chứa JavaScript hoặc frontend behavior scripts.
- `images/` chứa ảnh, icon, illustration và các asset tĩnh phục vụ giao diện.
- Trong `styles/` và `scripts/`, tiếp tục phân namespace theo module tương ứng, ví dụ `staticfiles/styles/identity/...`, `staticfiles/scripts/reconcile/...`.
- Mỗi template hoặc static asset mới phải nằm dưới namespace module tương ứng.
- Không viết inline CSS hoặc inline JavaScript trực tiếp trong template, trừ trường hợp rất nhỏ và có lý do rõ ràng được review.
- Không viết inline CSS hoặc inline JavaScript trực tiếp trong Django template, trừ trường hợp rất nhỏ và có lý do rõ ràng được review.
- Khi xây dựng template, toàn bộ CSS và JavaScript phải được tách ra file riêng và quản lý trong `staticfiles/`.
- `staticfiles/` phải được chia thành ba nhóm chính: `styles/`, `scripts/`, và `images/`.
- Bên trong `styles/` và `scripts/`, tiếp tục phân namespace theo từng module context, ví dụ `staticfiles/styles/reconcile/...` hoặc `staticfiles/scripts/crf/...`.
- `images/` dùng để quản lý ảnh, icon, illustration hoặc asset tĩnh phục vụ giao diện; nếu cần ownership rõ hơn thì tiếp tục phân namespace theo module bên trong `images/`.
- Template chỉ được tham chiếu tới static assets thông qua namespace phù hợp với module sở hữu giao diện đó.
