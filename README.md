# Vanguardian

Vanguardian là nền tảng phần mềm phục vụ quản lý dữ liệu lâm sàng và vận hành nghiên cứu thử nghiệm lâm sàng theo hướng EDC. Ở góc nhìn business, hệ thống này được xây dựng để giúp sponsor, CRO, study team, data manager và các nhóm vận hành kiểm soát vòng đời dữ liệu nghiên cứu từ khâu thiết kế CRF, thu thập dữ liệu tại site, theo dõi chất lượng dữ liệu, xử lý sai khác, audit trail cho đến xuất dữ liệu và báo cáo điều hành.

Về mặt sản phẩm, Vanguardian hướng tới bài toán giảm phân mảnh dữ liệu nghiên cứu, tăng khả năng truy vết thay đổi, chuẩn hóa quyền truy cập dữ liệu nhạy cảm và rút ngắn thời gian làm sạch dữ liệu trước các mốc review, lock hoặc export. Về mặt kỹ thuật, repo được phát triển theo DDD và modular monolith để giữ bounded context rõ ràng, tránh trộn lẫn nghiệp vụ giữa các mảng như `identity`, `study`, `crf`, `datacapture`, `reconcile`, `audit`, `governance`, `exporting` và `dashboard`.

## Nguyên tắc triển khai

- Kiến trúc mặc định là modular monolith, mỗi bounded context phải giữ boundary và ownership rõ ràng.
- Schema nghiệp vụ không lấy Django migrations làm nguồn sự thật; thay đổi schema phải đi qua `db/dbdiagram.dbml` và `db/migrations/*.sql`.
- Trước khi mở rộng nghiệp vụ, cần đọc `src/AGENT.md`.

## Khởi tạo source local

Flow dưới đây là flow chuẩn để dựng môi trường local theo đúng định hướng hiện tại của repo.

### 1. Chuẩn bị môi trường

Yêu cầu:

- Python `3.14+`
- Docker + Docker Compose
- Công cụ build cho `mysqlclient` trên máy local

Tạo virtualenv và cài dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 2. Tạo file cấu hình môi trường

```bash
cp src/.env.tpl src/.env
```

Mặc định file này đã trỏ về MariaDB và Memcached chạy trên host:

- MariaDB: `127.0.0.1:3306`
- Memcached: `127.0.0.1:11211`

### 3. Khởi động hạ tầng local

```bash
docker compose -f docker/docker-compose.yml up -d mariadb memcached
```

Nếu cần luồng workflow đầy đủ hơn, có thể bật thêm `mosquitto` và `node-red`:

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 4. Init database theo DB-first

Khởi tạo các bảng nền của Django trước:

```bash
python manage.py migrate contenttypes
python manage.py migrate auth
```

Apply toàn bộ SQL nghiệp vụ trong `db/migrations/` vào MariaDB:

```bash
for file in db/migrations/*.sql; do
  docker exec -i vanguardian-mariadb \
    mariadb -uvanguardian -pvanguardian vanguardian < "$file"
done
```

Đánh dấu migration state cho app `identity` mà không để Django tự tạo schema:

```bash
python manage.py migrate identity --fake
```

Chạy migrate tổng cho các bảng còn lại:

```bash
python manage.py migrate
```

Nếu cần tài khoản quản trị để đăng nhập nhanh:

```bash
python manage.py createsuperuser
```

### 5. Chạy source

```bash
python manage.py runserver
```

Các URL chính:

- `http://127.0.0.1:8000/login/`
- `http://127.0.0.1:8000/dashboard/`
- `http://127.0.0.1:8000/admin/`

## Tài liệu nên đọc trước khi phát triển

- `src/AGENT.md`
- `docs/db-first-migrate-guide.md`
- `db/dbdiagram.dbml`
