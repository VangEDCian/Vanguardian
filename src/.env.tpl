# -----------------------------------------------------------------------------
# Django core settings (used in src/Vanguardian/settings.py)
# -----------------------------------------------------------------------------
SECRET_KEY=django-insecure-secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
TZ=Asia/Ho_Chi_Minh

# -----------------------------------------------------------------------------
# Database and cache URLs used by django-environ
# -----------------------------------------------------------------------------
# Source runs on host machine (connect to docker services via published ports)
DATABASE_URL=mysql://vanguardian:vanguardian@127.0.0.1:3306/vanguardian
CACHE_URL=memcache://127.0.0.1:11211

# If source runs inside the same docker network, switch to service DNS names:
# DATABASE_URL=mysql://vanguardian:vanguardian@mariadb:3306/vanguardian
# CACHE_URL=memcache://memcached:11211

MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_WS_PORT=9001
MQTT_URL=mqtt://127.0.0.1:1883

NODE_RED_HOST=127.0.0.1
NODE_RED_PORT=1880
NODE_RED_URL=http://127.0.0.1:1880
