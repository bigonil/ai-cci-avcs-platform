.PHONY: help install lint format typecheck test test-integration test-live test-e2e \
        coverage up up-obs up-dev down build logs \
        demo demo-all demo-hera demo-aou demo-semsotec demo-ducati demo-dallara demo-prada \
        demo-dry-run verify-audit pre-commit clean mem-check

PYTHON   := python3
UV       := uv
COMPOSE  := docker compose
SCENARIO := $(UV) run python scripts/run_demo_scenario.py

help: ## Mostra questo messaggio
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Sviluppo
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

test: ## Unit test (no containers, no live LLM)
	$(UV) run pytest -m "not integration and not live_llm" --cov=. --cov-report=term-missing

test-integration: ## Integration test con testcontainers (richiede Docker)
	$(UV) run pytest -m integration --cov=. --cov-report=term-missing

test-live: ## Test con Anthropic API reale (richiede ANTHROPIC_API_KEY)
	$(UV) run pytest -m live_llm -v

test-e2e: up ## Scenario end-to-end (tutti i domini)
	$(UV) run pytest tests/e2e/ -v

coverage: ## Report coverage HTML
	$(UV) run pytest -m "not integration and not live_llm" \
		--cov=. --cov-report=html --cov-report=term-missing
	@echo "Report: htmlcov/index.html"

# ---------------------------------------------------------------------------
# Infrastruttura
# ---------------------------------------------------------------------------

up: ## Avvia stack core (≤ 2.65 GB RAM, senza observability)
	$(COMPOSE) up -d
	@echo "Waiting for services..."
	@sleep 5
	$(COMPOSE) ps

up-dev: ## Avvia stack con frontend in hot-reload (Vite HMR su :5173, BFF su :8080)
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d

up-obs: ## Avvia stack core + observability (≤ 2.95 GB RAM — Prometheus, Grafana, Tempo)
	$(COMPOSE) --profile observability up -d
	@echo "Waiting for services..."
	@sleep 5
	$(COMPOSE) ps

down: ## Ferma infrastruttura docker-compose
	$(COMPOSE) down

build: ## Build immagini Docker dei servizi
	$(COMPOSE) build

logs: ## Segui i log di tutti i servizi
	$(COMPOSE) logs -f

mem-check: ## Mostra RAM usata da ogni container (richiede stack attivo)
	@docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" \
		2>/dev/null | sort -k2 -rh || echo "Stack non attivo — esegui make up"

# ---------------------------------------------------------------------------
# Demo scenari — tutti i domini verticali
# ---------------------------------------------------------------------------

demo: demo-all ## Alias: esegui tutti gli scenari demo (richiede make up)

demo-all: up ## Esegui tutti gli scenari pilota (hera, aou, semsotec, ducati, dallara, prada)
	$(SCENARIO) --domain all

demo-hera: up ## Scenario pilota: Hera Group IT — Cloud commitment vs Budget vs ISO 27001 Q1 2026
	$(SCENARIO) --domain hera_it

demo-aou: up ## Scenario pilota: AOU Modena — Sperimentazione clinica senza approvazione etica
	$(SCENARIO) --domain aou_clinical

demo-semsotec: up ## Scenario pilota: SEMSOTEC — Prodotto ON_MARKET con certificazione CE scaduta
	$(SCENARIO) --domain semsotec_product

demo-ducati: up ## Scenario pilota: Ducati Corse — Omologazione FIM scaduta, budget cap, token esauriti
	$(SCENARIO) --domain ducati_corse

demo-dallara: up ## Scenario pilota: Dallara — IR18 IndyCar con crash test FIA scaduto
	$(SCENARIO) --domain dallara

demo-prada: up ## Scenario pilota: Prada Group — DPP e fornitori non certificati FW2026
	$(SCENARIO) --domain prada

demo-dry-run: ## Mostra il piano di tutti gli scenari senza chiamare i servizi (utile in CI)
	$(SCENARIO) --domain all --dry-run

# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------

verify-audit: ## Verifica integrità hash chain audit log MongoDB
	$(UV) run python scripts/verify_audit_chain.py

# ---------------------------------------------------------------------------
# Gate qualità
# ---------------------------------------------------------------------------

pre-commit: lint typecheck test ## Gate pre-commit completo (lint + typecheck + unit test)

# ---------------------------------------------------------------------------
# Pulizia
# ---------------------------------------------------------------------------

clean: ## Rimuovi artefatti build e cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf demo_output/
