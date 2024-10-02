# Defaults here

-include .env

# PYTHON STUFF
PYTHON := python3.12

.venv:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install --upgrade uv

requirements.txt: pyproject.toml | .venv
	.venv/bin/python -m uv pip compile \
		--no-emit-index-url \
		--generate-hashes \
		--all-extras \
		--upgrade \
		--output-file $@ \
		pyproject.toml

.venv/sentinel: requirements.txt | .venv
	.venv/bin/python -m uv pip sync \
		requirements.txt
	.venv/bin/python -m uv pip install --editable .
	touch $@

# ACTUAL COMMANDS

.PHONY: develop
develop: .venv/sentinel

.PHONY: type-check
type-check: | develop
	.venv/bin/mypy

.PHONY: format
format: | develop
	.venv/bin/python -m black src tests examples
	.venv/bin/ruff check --fix

.PHONY: clean-redis
clean-redis:
	docker stop ${REDIS_CONTAINER} || true
	docker rm ${REDIS_CONTAINER} || true

.PHONY: redis
redis: clean-redis
	scripts/redis.sh
