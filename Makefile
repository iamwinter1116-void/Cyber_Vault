.PHONY: preflight secrets db-up db-down

PYTHON ?= python3

preflight:
	sh host/preflight.sh

secrets:
	$(PYTHON) db/init/generate_secrets.py

db-up:
	docker compose up -d --wait db

db-down:
	docker compose stop db
