.PHONY: help install dev test test-unit test-integration lint format type-check clean run fetch config

# Default target - show help
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
UV := uv
PACKAGE := finfolio
SRC_DIR := finfolio
TEST_DIR := tests
PYTEST := $(UV) run pytest

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)FinFolio - YouTube Transcript Fetch Module$(NC)"
	@echo ""
	@echo "$(GREEN)Usage: make [target]$(NC)"
	@echo ""
	@echo "$(BLUE)Installation & Setup:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(install|dev|config)' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)Development:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(test|lint|format|type)' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)Running:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(run|fetch|start)' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)Maintenance:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(clean)' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make install        # Install all dependencies"
	@echo "  make fetch          # Run finfolio fetch command"
	@echo "  make test           # Run all tests"
	@echo "  make lint           # Run linting checks"

# ============================================================================
# Installation & Setup
# ============================================================================

install: ## Install production dependencies with uv
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(UV) pip install click "google-api-python-client>=2.100.0" pyyaml "python-dotenv>=1.0.0"
	$(UV) pip install -e .
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

dev: ## Install all dependencies including dev tools
	@echo "$(BLUE)Installing all dependencies (production + dev)...$(NC)"
	$(UV) sync
	$(UV) pip install -e .
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

config: ## Create .env file from template
	@if [ -f .env ]; then \
		echo "$(YELLOW)⚠ .env already exists. Use 'make config-reset' to overwrite.$(NC)"; \
	else \
		cp .env.example .env; \
		echo "$(GREEN)✓ Created .env from template$(NC)"; \
		echo "$(YELLOW)⚠ Edit .env and set YOUTUBE_API_KEY before running fetch$(NC)"; \
	fi

config-reset: ## Reset .env from template (overwrites existing)
	@echo "$(YELLOW)Resetting .env from template...$(NC)"
	cp .env.example .env
	@echo "$(GREEN)✓ .env reset$(NC)"

config-channels: ## Create channels.yaml from template
	@if [ -f channels.yaml ]; then \
		echo "$(YELLOW)⚠ channels.yaml already exists. Use 'make config-channels-reset' to overwrite.$(NC)"; \
	else \
		cp channels.yaml.example channels.yaml; \
		echo "$(GREEN)✓ Created channels.yaml from template$(NC)"; \
		echo "$(YELLOW)⚠ Edit channels.yaml to add your YouTube financial channels$(NC)"; \
	fi

config-channels-reset: ## Reset channels.yaml from template (overwrites existing)
	@echo "$(YELLOW)Resetting channels.yaml from template...$(NC)"
	cp channels.yaml.example channels.yaml
	@echo "$(GREEN)✓ channels.yaml reset$(NC)"

# ============================================================================
# Development & Testing
# ============================================================================

test: test-unit test-integration ## Run all tests

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(PYTEST) $(TEST_DIR)/unit/ -v --cov=$(SRC_DIR) --cov-report=term-missing

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTEST) $(TEST_DIR)/integration/ -v

test-coverage: ## Run tests with detailed coverage report
	@echo "$(BLUE)Running tests with coverage report...$(NC)"
	$(PYTEST) $(TEST_DIR)/ -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✓ Coverage report generated: htmlcov/index.html$(NC)"

test-fast: ## Run tests without coverage (faster)
	@echo "$(BLUE)Running tests (fast mode)...$(NC)"
	$(PYTEST) $(TEST_DIR)/ -v --no-cov

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	$(UV) run ptw $(TEST_DIR)/ -- -v

lint: ## Run ruff linting
	@echo "$(BLUE)Running ruff linter...$(NC)"
	$(UV) run ruff check $(SRC_DIR)/ $(TEST_DIR)/
	@echo "$(GREEN)✓ Linting passed$(NC)"

lint-fix: ## Run ruff linting with auto-fix
	@echo "$(BLUE)Running ruff linter with auto-fix...$(NC)"
	$(UV) run ruff check --fix $(SRC_DIR)/ $(TEST_DIR)/
	@echo "$(GREEN)✓ Linting issues fixed$(NC)"

format: ## Format code with ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	$(UV) run ruff format $(SRC_DIR)/ $(TEST_DIR)/
	@echo "$(GREEN)✓ Code formatted$(NC)"

type-check: ## Run mypy type checking
	@echo "$(BLUE)Running mypy type checker...$(NC)"
	$(UV) run mypy $(SRC_DIR)/ --ignore-missing-imports
	@echo "$(GREEN)✓ Type checking passed$(NC)"

quality: lint type-check ## Run all quality checks (lint + type-check)
	@echo "$(GREEN)✓ All quality checks passed$(NC)"

# ============================================================================
# Running & Operations
# ============================================================================

fetch: ## Run finfolio fetch command
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠ .env file not found. Creating from template...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)⚠ Please edit .env and set YOUTUBE_API_KEY$(NC)"; \
		exit 1; \
	fi
	@if [ ! -f channels.yaml ]; then \
		echo "$(YELLOW)⚠ channels.yaml not found. Creating from template...$(NC)"; \
		cp channels.yaml.example channels.yaml; \
		echo "$(YELLOW)⚠ Please edit channels.yaml with your channels$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running finfolio fetch...$(NC)"
	$(UV) run finfolio fetch

fetch-config: ## Run finfolio fetch with custom config file (CONFIG=path/to/channels.yaml)
	@if [ -z "$(CONFIG)" ]; then \
		echo "$(YELLOW)Usage: make fetch-config CONFIG=path/to/channels.yaml$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running finfolio fetch with custom config: $(CONFIG)$(NC)"
	$(UV) run finfolio fetch --config $(CONFIG)

fetch-dry-run: ## Simulate fetch without downloading (for testing)
	@echo "$(BLUE)Simulating fetch (dry-run)...$(NC)"
	@echo "Note: Dry-run not yet implemented. Use 'make fetch' to test with real API."

fetch-help: ## Show finfolio fetch command help
	@echo "$(BLUE)FinFolio fetch help:$(NC)"
	$(UV) run finfolio fetch --help

start: fetch ## Alias for 'fetch' - start the fetch process

# ============================================================================
# Maintenance
# ============================================================================

clean: clean-python clean-coverage clean-build clean-storage ## Clean all generated files

clean-python: ## Remove Python cache files
	@echo "$(BLUE)Cleaning Python cache...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Python cache cleaned$(NC)"

clean-coverage: ## Remove coverage reports
	@echo "$(BLUE)Cleaning coverage reports...$(NC)"
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "$(GREEN)✓ Coverage reports removed$(NC)"

clean-build: ## Remove build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info/ .eggs/
	@echo "$(GREEN)✓ Build artifacts removed$(NC)"

clean-storage: ## Remove local storage and state files (WARNING: removes transcripts!)
	@echo "$(YELLOW)⚠ WARNING: This will remove all downloaded transcripts!$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf storage/; \
		echo "$(GREEN)✓ Storage cleaned$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

clean-env: ## Remove .env and channels.yaml (WARNING: removes local configuration!)
	@echo "$(YELLOW)⚠ WARNING: This will remove your local configuration!$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f .env channels.yaml; \
		echo "$(GREEN)✓ Configuration removed$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

clean-all: ## Deep clean (removes storage, .env, channels.yaml, and all build artifacts)
	@echo "$(YELLOW)⚠ WARNING: This is a destructive operation!$(NC)"
	@read -p "This will remove: storage, .env, channels.yaml, and all build artifacts. Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		make clean; \
		rm -rf storage/ .env channels.yaml; \
		echo "$(GREEN)✓ Deep clean complete$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# ============================================================================
# Utilities
# ============================================================================

check-status: ## Show project status (Git, storage, config)
	@echo "$(BLUE)Project Status:$(NC)"
	@echo ""
	@echo "$(BLUE)Git Status:$(NC)"
	@git status --short | head -10 || echo "  ✓ No changes"
	@echo ""
	@echo "$(BLUE)Configuration Files:$(NC)"
	@test -f .env && echo "  ✓ .env exists" || echo "  ✗ .env missing (run 'make config')"
	@test -f channels.yaml && echo "  ✓ channels.yaml exists" || echo "  ✗ channels.yaml missing (run 'make config-channels')"
	@echo ""
	@echo "$(BLUE)Storage:$(NC)"
	@if [ -d storage/transcripts ]; then \
		count=$$(find storage/transcripts -name "*.txt" 2>/dev/null | wc -l); \
		echo "  ✓ storage/transcripts/ exists ($$count transcripts)"; \
	else \
		echo "  ✗ storage/transcripts/ not created yet"; \
	fi
	@echo ""
	@echo "$(BLUE)Dependencies:$(NC)"
	@if $(UV) pip list --quiet 2>/dev/null | grep -q click; then \
		echo "  ✓ Dependencies installed"; \
	else \
		echo "  ✗ Dependencies not installed (run 'make install')"; \
	fi

ls-storage: ## List downloaded transcripts
	@if [ -d storage/transcripts ]; then \
		echo "$(BLUE)Downloaded transcripts:$(NC)"; \
		ls -lah storage/transcripts/ | tail -n +2; \
	else \
		echo "$(YELLOW)No transcripts downloaded yet$(NC)"; \
	fi

view-logs: ## View recent JSON logs (requires tail)
	@echo "$(BLUE)Recent activity (last 20 lines):$(NC)"
	@tail -20 finfolio.log 2>/dev/null || echo "$(YELLOW)No logs found$(NC)"

# ============================================================================
# Docker Support (Optional)
# ============================================================================

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	@echo "$(YELLOW)Note: Do not run docker build per user constraints$(NC)"
	@echo "Build manually with: docker build -t finfolio ."

docker-run: ## Run finfolio in Docker (requires pre-built image)
	@echo "$(BLUE)Running finfolio in Docker...$(NC)"
	docker run --rm -v $$(pwd)/.env:/.env -v $$(pwd)/channels.yaml:/channels.yaml -v $$(pwd)/storage:/storage finfolio fetch

# ============================================================================
# Setup Complete Message
# ============================================================================

setup: install config config-channels ## Complete setup (install deps + create config files)
	@echo ""
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Edit .env and set your YOUTUBE_API_KEY"
	@echo "  2. Edit channels.yaml and add your YouTube channels"
	@echo "  3. Run: $(GREEN)make fetch$(NC)"
	@echo ""
	@echo "$(BLUE)Other useful commands:$(NC)"
	@echo "  $(GREEN)make test$(NC)          - Run the test suite"
	@echo "  $(GREEN)make quality$(NC)       - Run linting and type checks"
	@echo "  $(GREEN)make help$(NC)          - Show this help message"
