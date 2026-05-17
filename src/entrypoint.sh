#!/bin/sh
set -e

python ./manage.py collectstatic --noinput

exec uvicorn configs.asgi:application \
	--host 0.0.0.0 \
	--port 8000
