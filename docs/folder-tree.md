# Folder Tree đề xuất

```bash
.
├── AGENT.md
├── docker
│   └── docker-compose.yml
├── docs
│   └── folder-tree.md
├── manage.py
├── README.md
├── src
│   ├── apps
│   │   ├── audit_compliance
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   ├── clinical_capture
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   ├── data_review
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   ├── identity_access
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   ├── operational_tracking
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   ├── query_management
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   ├── reporting_export
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   ├── shared_kernel
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   ├── study_design
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   ├── study_operations
│   │   │   ├── application
│   │   │   ├── domain
│   │   │   ├── infrastructure
│   │   │   ├── presentation
│   │   │   └── README.md
│   │   └── user_administration
│   │       ├── application
│   │       ├── domain
│   │       ├── infrastructure
│   │       ├── presentation
│   │       └── README.md
│   ├── Dockerfile
│   └── Vanguardian
│       ├── __init__.py
│       ├── 󰌠 __pycache__
│       │   ├── __init__.cpython-314.pyc
│       │   ├── settings.cpython-314.pyc
│       │   ├── urls.cpython-314.pyc
│       │   └── wsgi.cpython-314.pyc
│       ├── asgi.py
│       ├── settings.py
│       ├── urls.py
│       └── wsgi.py
└── tests
```

## Ghi chú

- `presentation/` có thể là REST API, admin adapter, internal CLI hoặc message handler.
- `reporting_export` và `operational_tracking` thường thiên về read model hơn aggregate giàu hành vi.
- Có thể thêm `migrations/` ở root hoặc tại từng context, nhưng phải giữ ownership rõ ràng.
