# DB-First + Django Migrate Guide

Mục tiêu:

- Vẫn dùng `./manage.py migrate` để khởi tạo/cập nhật các bảng thư viện Django (`contenttypes`, `auth`, `admin`, `sessions`).
- Schema nghiệp vụ `identity` vẫn theo DB-first (SQL ở `db/migrations/*.sql` là nguồn sự thật).

## Nguyên tắc

- Không đặt DDL nghiệp vụ vào Django migration như nguồn chính.
- DDL nghiệp vụ `identity` nằm trong các file SQL tại `db/migrations/*.sql`.
- Django migrations của `identity` chỉ giữ **state mapping** (managed=False), không sở hữu schema.
- `auth_permission` sẽ được tạo bởi Django trong `migrate` dựa trên `django_content_type` và `Meta.permissions`.

## Quy trình khởi tạo DB mới

1. Khởi động MariaDB:

```bash
docker compose -f docker/docker-compose.yml up -d mariadb
```

1. Chạy migrate cho thư viện Django cần làm nền:

```bash
./manage.py migrate contenttypes
./manage.py migrate auth
```

1. Apply SQL DB-first cho `identity`:

```bash
for file in db/migrations/*.sql; do
  docker exec -i vanguardian-mariadb \
    mariadb -uvanguardian -pvanguardian vanguardian < "$file"
done
```

1. Đánh dấu migration state của `identity` (không chạy DDL qua Django):

```bash
./manage.py migrate identity --fake
```

1. Chạy migrate tổng:

```bash
./manage.py migrate
```

## Quy trình khi có thay đổi schema nghiệp vụ

1. Cập nhật `db/dbdiagram.dbml`.
2. Thêm SQL mới trong `db/migrations/*.sql`.
3. Apply SQL bằng MariaDB client.
4. Nếu cần cập nhật state Django model, tạo migration state-only và chạy `--fake` (không dùng Django migration để tạo/bẻ schema nghiệp vụ).

## Xử lý lỗi thường gặp

### 1) `InconsistentMigrationHistory` (identity chạy trước auth)

```bash
./manage.py migrate identity zero --fake
./manage.py migrate auth
./manage.py migrate identity --fake
./manage.py migrate
```

Nếu vẫn lỗi, kiểm tra bảng `django_migrations` và xóa record `identity/0001_initial` rồi chạy lại flow trên.

### 2) `errno: 150 Foreign key constraint is incorrectly formed` khi tạo `django_admin_log`

Nguyên nhân thường gặp: bảng `identity_user` chưa tồn tại trước khi chạy `admin.0001`.

Khắc phục: chạy lại đúng thứ tự:

- migrate `contenttypes`, `auth`
- apply toàn bộ `db/migrations/*.sql`
- `./manage.py migrate identity --fake`
- `./manage.py migrate`
