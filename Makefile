.PHONY: help install format lint lint-fix typecheck docstring style fix \
        check sync clean test stats watch live-stream run-client reclaim \
        monitor monitor-charts
.DEFAULT_GOAL := help

# Always run full test suite without fail-fast
TEST_FLAGS := -vv -s -p no:anchorpy

format: ## Format code using ruff
	uv run ruff format .
	uv run ruff check --fix --unsafe-fixes .

typecheck: ## Run static type checking
	uv run ty check framework/ smm/ tests/

fix: ## Run all formatters and typecheck
	$(MAKE) format typecheck

sync: ## Re‑lock and install latest versions
	uv lock --upgrade       # rebuild uv.lock with newer pins
	uv sync --all-groups    # install everything into .venv

clean: ## Remove build artefacts and caches
	rm -rf .ruff_cache/ .mypy_cache/ .pytest_cache/ dist/ build/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

test: ## Run tests
	uv run pytest $(TEST_FLAGS)

# Pattern rule so additional args do not trigger "No rule to make target"
%:
	@:

help: ## Display this help message
	@echo 'Usage:'
	@echo '  make <target>'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
