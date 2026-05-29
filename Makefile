.PHONY: help install lint typecheck test test-integration test-e2e coverage \
        up down build logs demo verify-audit clean

PYTHON := python3
UV     := uv
COMPOSE := docker compose

help: ## Mostra questo messaggio
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

install: ## Installa dipendenze (uv sync workspace)
	$(UV) sync --all-packages

lint: ## Ruff lint + format check su tutto il monorepo
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Formatta il codice con Ruff
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

typecheck: ## mypy --strict su tutti i package
	$(UV) run mypy libs/cci-common/src libs/cci-llm/src \
		services/ingestion/src services/knowledge/src \
		services/retrieval/src services/coherence/src \
		services/agents/src services/governance/src

test: ## Unit test (no containers, no live LLM)
	$(UV) run pytest -m "not integration and not live_llm" --cov=. --cov-report=term-missing

test-integration: ## Integration test con testcontainers (richiede Docker)
	$(UV) run pytest -m integration --cov=. --cov-report=term-missing

test-live: ## Test con Anthropic API reale (richiede ANTHROPIC_API_KEY)
	$(UV) run pytest -m live_llm -v

test-e2e: up ## Scenario end-to-end Hera Q1 2026
	$(UV) run pytest tests/e2e/ -v

coverage: ## Report coverage HTML
	$(UV) run pytest -m "not integration and not live_llm" \
		--cov=. --cov-report=html --cov-report=term-missing
	@echo "Report: htmlcov/index.html"

up: ## Avvia infrastruttura docker-compose
	$(COMPOSE) up -d
	@echo "Waiting for services..."
	@sleep 5
	$(COMPOSE) ps

down: ## Ferma infrastruttura docker-compose
	$(COMPOSE) down

build: ## Build immagini Docker dei servizi
	$(COMPOSE) build

logs: ## Segui i log di tutti i servizi
	$(COMPOSE) logs -f

demo: up ## Esegui scenario demo Hera Q1 2026
	$(UV) run python scripts/run_demo_scenario.py

verify-audit: ## Verifica integrità hash chain audit log
	$(UV) run python scripts/verify_audit_chain.py

pre-commit: lint typecheck test ## Gate pre-commit completo

clean: ## Rimuovi artefatti build e cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
