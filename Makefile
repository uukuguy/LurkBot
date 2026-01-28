.PHONY: help install dev test lint format typecheck clean run gateway

# Default target
help:
	@echo "LurkBot - Multi-channel AI Assistant Platform"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup:"
	@echo "  install     Install production dependencies"
	@echo "  dev         Install development dependencies"
	@echo "  sync        Sync all dependencies with lockfile"
	@echo ""
	@echo "Development:"
	@echo "  test        Run tests with pytest"
	@echo "  test-cov    Run tests with coverage report"
	@echo "  lint        Run ruff linter"
	@echo "  format      Format code with ruff"
	@echo "  typecheck   Run mypy type checker"
	@echo "  check       Run all checks (lint, typecheck, test)"
	@echo ""
	@echo "Run:"
	@echo "  gateway     Start the gateway server"
	@echo "  cli         Run CLI commands (use ARGS='...')"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean       Remove build artifacts and caches"
	@echo "  update      Update dependencies"

# ============================================================================
# Setup
# ============================================================================

install:
	uv sync --no-dev

dev:
	uv sync --all-extras

sync:
	uv sync

# ============================================================================
# Development
# ============================================================================

test:
	uv run pytest -xvs

test-cov:
	uv run pytest --cov=src/lurkbot --cov-report=term-missing --cov-report=html

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

typecheck:
	uv run mypy src

check: lint typecheck test

# ============================================================================
# Run
# ============================================================================

gateway:
	uv run lurkbot gateway start

cli:
	uv run lurkbot $(ARGS)

# ============================================================================
# Maintenance
# ============================================================================

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	rm -rf dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

update:
	uv lock --upgrade
	uv sync
