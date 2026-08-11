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
	$(PYTHON) -c "import multiprocessing as mp, sys; mp.set_start_method('fork'); from djlint import main; sys.argv=['djlint','src/templates']; raise SystemExit(main())"
	flake8 --select DDD,DJG -j 1 .
	ruff check .

shell:
	$(PYTHON) manage.py shell
