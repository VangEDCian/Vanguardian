PYTHON ?= python
DJANGO_SETTINGS_MODULE ?= Vanguardian.settings_test
ENV_FILE ?= src/.env.test

export DJANGO_SETTINGS_MODULE
export VANGUARDIAN_ENV_FILE := $(abspath $(ENV_FILE))
export PYTHONPATH := $(abspath src)

.PHONY: infra-up infra-down migrate test lint shell

infra-up:
	docker compose -f docker/docker-compose.yml up -d mariadb memcached

infra-down:
	docker compose -f docker/docker-compose.yml down

migrate:
	$(PYTHON) manage.py migrate

test:
	$(PYTHON) manage.py test tests --verbosity 1 --noinput

lint:
	djlint src/templates
	flake8 --select DDD,DJG .
	ruff check .

shell:
	$(PYTHON) manage.py shell
