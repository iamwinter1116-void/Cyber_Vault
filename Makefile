.PHONY: preflight secrets db-up db-down up down check-fast budget-report test-contract test-security test-e2e scan openapi evidence demo-reset tamper-drill

ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
PYTHON ?= python3
endif

CASE ?=

preflight:
	sh host/preflight.sh

secrets:
	$(PYTHON) db/init/generate_secrets.py

db-up:
	docker compose up -d --wait db

db-down:
	docker compose stop db

up:
	$(PYTHON) db/init/require.py up
	docker compose up -d --wait

down:
	docker compose down

check-fast:
	$(PYTHON) db/init/report_budgets.py
	$(PYTHON) db/init/require.py check-fast
	$(PYTHON) -m ruff check core services tests/unit
	$(PYTHON) -m mypy --strict core/abh_core services/api services/notary services/runner tests/unit
	cd web && npx --no-install tsc --noEmit
	$(PYTHON) -m pytest tests/unit db/init/test_generate_secrets.py -q
	$(PYTHON) db/init/require.py placeholders

budget-report:
	$(PYTHON) db/init/report_budgets.py

test-contract:
	$(PYTHON) db/init/require.py test-contract
	$(PYTHON) -m pytest tests/contract -q

test-security:
	$(PYTHON) db/init/require.py test-security
	$(PYTHON) -m pytest tests/security -q

test-e2e:
	$(PYTHON) db/init/require.py test-e2e
	$(PYTHON) -m pytest tests/e2e -q

scan:
	$(PYTHON) db/init/require.py scan
	$(PYTHON) db/init/run_scans.py

openapi:
	$(PYTHON) -m services.api.openapi_export

evidence:
	$(PYTHON) tools/collect_evidence.py

demo-reset:
	$(PYTHON) db/init/require.py demo-reset
	$(PYTHON) db/init/demo_reset.py

tamper-drill:
	$(PYTHON) tools/tamper_drill.py --case "$(CASE)"
