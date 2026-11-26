.PHONY: preflight db-up db-down

preflight:
	sh host/preflight.sh

db-up:
	docker compose up -d --wait db

db-down:
	docker compose stop db
