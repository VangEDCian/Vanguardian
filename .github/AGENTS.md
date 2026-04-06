# AGENTS Guide for Vanguardian

## Big Picture (Modular Monolith + DDD)
- Core contexts live under `src/apps/`: `identity`, `study`, `audit`, `dashboard`, and `shared` (registered in `src/Vanguardian/settings.py` via `X_INSTALLED_APPS`).
- HTTP entrypoints are web-focused CBVs in `presentation/web`, wired in `src/Vanguardian/urls.py` and each app's `presentation/web/urls.py`.
- Business logic is pushed into `application` services/queries; views orchestrate commands and permissions (see `CreateStudyService` in `src/apps/study/application/commands/create_study.py`).
- Cross-context events flow through `audit` via `AuditContextAdapter` (`src/apps/audit/public.py`), used by services like `StudyAuditService` and `IdentityUserAuditService`.

## Layering and Boundaries You Should Preserve
- Keep imports one-way: `presentation -> application -> infrastructure`, with persistence models in `infrastructure/persistence`.
- Public surface is intentionally re-exported in `application/__init__.py` (for example `src/apps/study/application/__init__.py`); prefer importing from the package root.
- DB tables are DB-first and mostly `managed = False` models (`src/apps/identity/infrastructure/persistence/models.py`, `src/apps/study/infrastructure/persistence/models/study.py`).
- Soft-delete is a core invariant: business queries/services filter `deleted=False` before acting.

## Database + Migration Workflow (Project-Specific)
- Source of truth for business schema is SQL migrations under `db/migrations/`, not Django-generated migrations (`README.md`, `db/migrations/*.sql`).
- Local bootstrap order from `README.md`: migrate `contenttypes`/`auth`, apply SQL files, run `python manage.py migrate identity --fake`, then `python manage.py migrate`.
- If adding a table/column used by domain models, update SQL migration files first, then align Django model metadata (`db_table`, indexes, permissions).

## AuthZ/AuthN and Request Flow Details
- Custom user model is `identity.User` (`AUTH_USER_MODEL` in `src/Vanguardian/settings.py`) with custom backend `IdentifierBackend` for username/email/phone login.
- Global membership gate is middleware `MembershipAccessMiddleware` (`src/apps/identity/infrastructure/auth/middleware.py`); new authenticated routes must consider membership requirements.
- Permissions are granular and model-defined (for example field-level `study.*` permissions in `src/apps/study/infrastructure/persistence/models/study.py`), and views enforce them explicitly.

## Coding Patterns Seen Across Contexts
- Command services use immutable dataclass commands (`CreateIdentityUserCommand`, `UpdateStudyCommand`) and an `execute()` method.
- Views keep business decisions out of templates: they map permission checks into context flags (see `StudyDetailView` and `IdentityUserDetailView`).
- Audit snapshots are explicit dict serializers (`serialize_identity_user_snapshot`, `_serialize_study_snapshot`) and included in create/update/delete flows.

## Developer Workflows
- Python target is `>=3.14` (`pyproject.toml`); dependencies installed with editable dev extras (`python -m pip install -e ".[dev]"`).
- Infra services for local dev are in `docker/docker-compose.yml` (`mariadb`, `memcached`, optional `mosquitto`).
- Run app with `python manage.py runserver`; tests currently live in `tests/identity/` and `tests/study/` and use `django.test.SimpleTestCase` + mocking.

## Existing AI/Contributor Guidance Found
- `README.md`: architecture principles + DB-first migration policy.
- `src/locale/README.md`: translation editing rules (`msgid` stays English; update `msgstr`, then rebuild `.mo`).
- Note: `README.md` references `src/AGENT.md`, but that file is not present in this workspace snapshot.

