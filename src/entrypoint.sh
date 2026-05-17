#!/bin/sh
set -e

cd /app

python manage.py collectstatic --noinput

exec python -m uvicorn Vanguardian.asgi:application \
	--host 0.0.0.0 \
	--port 8000
