PY := .venv/bin/python
.DEFAULT_GOAL := help

.PHONY: help venv check-venv check-node setup page-map extract verify ingest lint lint-web test test-web check clean-slices evals evals-check

help: ## Show available targets
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

# A fresh clone has neither .venv nor node_modules -- both are gitignored. Without
# these guards the first command someone runs dies on "no such file or directory",
# which says nothing about what to do next.
check-venv:
	@test -x $(PY) || { \
		echo "No virtualenv yet ($(PY) is missing)."; \
		echo "This is expected on a fresh clone -- .venv is gitignored."; \
		echo ""; \
		echo "  make setup     # creates it and installs both halves"; \
		exit 1; }

check-node:
	@test -d frontend/node_modules || { \
		echo "Front-end dependencies are not installed (frontend/node_modules is missing)."; \
		echo "This is expected on a fresh clone -- node_modules is gitignored."; \
		echo ""; \
		echo "  make setup     # creates the virtualenv and installs both halves"; \
		exit 1; }

setup: venv ## One command for a fresh clone: virtualenv, backend, front end
	cd frontend && npm install
	@echo ""
	@echo "Ready. Next:"
	@test -f backend/.env \
		&& echo "  make dev       # API on :8000, front end on :5173" \
		|| echo "  cp backend/.env.example backend/.env   # then add your ANTHROPIC_API_KEY"

venv: ## Create the virtualenv and install the backend
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -e "backend[dev]"

page-map: check-venv ## Calibrate printed <-> PDF page numbers (framework/page_map.json)
	$(PY) -m mindforge_assess.ingest.pdf_index

extract: check-venv ## Run the handbook extractors (all, or NAMES="a b")
	$(PY) -m mindforge_assess.ingest.extract $(NAMES)

verify: check-venv ## Check every extraction against the pages it came from
	$(PY) -m mindforge_assess.ingest.verify $(NAMES)

pack: check-venv ## Merge verified extractions into framework/pack.v1.json
	$(PY) -m mindforge_assess.ingest.build_pack $(PACK_FLAGS)

notes: check-venv ## Regenerate docs/FRAMEWORK_NOTES.md from the pack
	$(PY) -m mindforge_assess.ingest.notes

ingest: check-venv ## Full offline ingestion. Skips if the pack matches the PDF; FORCE=1 to redo
	$(PY) -m mindforge_assess.ingest.run $(if $(FORCE),--force,)

prompt: check-venv ## Regenerate prompts/system.rendered.md from the pack
	$(PY) -m mindforge_assess.prompts.build_system_prompt

api: check-venv ## Run the API alone on :8000
	$(PY) -m uvicorn mindforge_assess.api:app --reload --port 8000

web: check-node ## Run the Vite dev server alone on :5173
	cd frontend && npm run dev

dev: check-venv check-node ## Run both; the Vite dev server proxies /api to the backend
	@echo "backend  http://localhost:8000"
	@echo "frontend http://localhost:5173"
	@trap 'kill 0' EXIT INT TERM; \
		$(PY) -m uvicorn mindforge_assess.api:app --reload --port 8000 & \
		(cd frontend && npm run dev) & \
		wait

build-web: check-node ## Type-check and build the front end
	cd frontend && npx tsc --noEmit -p tsconfig.app.json && npx vite build

assess: check-venv ## One-off assessment: make assess Q="a description"
	$(PY) -m mindforge_assess.assessor "$(Q)"

evals: check-venv ## Run the gold set: make evals MODEL=claude-opus-5 N=3
	$(PY) backend/evals/run_evals.py --model $(or $(MODEL),claude-sonnet-5) -n $(or $(N),3)

evals-check: check-venv ## Validate the gold set against the pack without calling the API
	$(PY) backend/evals/run_evals.py --validate-only

lint-web: check-node ## ESLint and Prettier over the front end
	cd frontend && npx tsc --noEmit -p tsconfig.app.json && npm run lint && npm run format:check

lint: check-venv ## ruff, mypy, and checks that the prompt and gold set match the pack
	$(PY) -m ruff check backend/src backend/tests
	$(PY) -m mypy backend/src backend/tests
	$(PY) -m mindforge_assess.prompts.build_system_prompt --check
	$(PY) backend/evals/run_evals.py --validate-only

test: check-venv ## Run the backend test suite (never hits the API)
	$(PY) -m pytest backend/tests -q

test-web: check-node ## Run the front-end component tests
	cd frontend && npm run test

check: lint lint-web test test-web ## Everything a CI job would run

clean-slices: check-venv ## Drop cached page slices and upload IDs
	rm -rf backend/framework/_cache
