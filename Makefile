.PHONY: help install format lint lint-fix typecheck docstring style fix \
        check sync clean test stats watch live-stream run-client reclaim \
        monitor monitor-charts
.DEFAULT_GOAL := help

# Always run full test suite without fail-fast
TEST_FLAGS := -vv -s -p no:anchorpy

format: ## Format code using ruff
	uv run ruff format .

lint: ## Run linting using ruff
	uv run ruff check .

lint-fix: ## Run linting with automatic fixes
	uv run ruff check --fix .
	uv run ruff check --fix --unsafe-fixes .

typecheck: ## Run static type checking
	uv run pyright

docstring: ## Check docstring style and completeness
	uv run ruff check . --select D,PD

docstring-fix: ## Fix docstring style and completeness
	uv run ruff check --fix . --select D,PD
	uv run ruff check --fix --unsafe-fixes . --select D,PD

style: ## Check code style (without docstrings)
	uv run ruff check . --select E,W,F,I,N,UP,B,C4,SIM,TCH

style-fix: ## Fix code style (without docstrings)
	uv run ruff check --fix . --select E,W,F,I,N,UP,B,C4,SIM,TCH
	uv run ruff check --fix --unsafe-fixes . --select E,W,F,I,N,UP,B,C4,SIM,TCH

fix: format lint-fix docstring-fix style-fix ## Run all formatters and fixers

check: fix typecheck ## Run all checks (format, lint‑fix, typecheck)

sync: ## Re‑lock and install latest versions
	uv lock --upgrade       # rebuild uv.lock with newer pins
	uv sync --all-groups    # install everything into .venv

clean: ## Remove build artefacts and caches
	rm -rf .ruff_cache/ .mypy_cache/ .pytest_cache/ dist/ build/
	find . -type d -name __pycache__ -exec rm -rf {} +

test: ## Run tests
	uv run pytest $(TEST_FLAGS)

stats: ## Show code quality statistics
	@echo "=== Docstring Coverage ==="
	@uv run ruff check . --select D --statistics
	@echo "\n=== Missing Type Hints ==="
	@uv run  ruff check . --select ANN --statistics
	@echo "\n=== Style Issues ==="
	@uv run  ruff check . --select E,W,F,I,N --statistics


# Watch tests, optionally limited to a path:
#   make watch                → watch entire suite
#   make watch path/to/file   → watch single test file
watch:
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		uv run pytest-watcher . --runner "pytest tests $(TEST_FLAGS) -W ignore::DeprecationWarning"; \
	else \
		path_arg="$(filter-out $@,$(MAKECMDGOALS))"; \
		uv run pytest-watcher . --runner "pytest src/tests/$$path_arg $(TEST_FLAGS) -W ignore::DeprecationWarning"; \
	fi

# Pattern rule so additional args do not trigger "No rule to make target"
%:
	@:

help: ## Display this help message
	@echo 'Usage:'
	@echo '  make <target>'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
