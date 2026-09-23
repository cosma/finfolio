# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FinFolio** is a fact-checking system for finance content. The .gitignore suggests this will be a Python project, likely with a Streamlit UI for presenting fact-checks.

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (once established)
pip install -r requirements-dev.txt
```

### Running & Testing
```bash
# Run tests (use pytest)
pytest

# Run a single test
pytest path/to/test.py::test_function_name

# Run tests with coverage
pytest --cov=src tests/

# Type checking (once mypy config is added)
mypy src/

# Linting and formatting
ruff check src/ tests/
ruff format src/ tests/
```

### Running the Application
```bash
# Start Streamlit app (once app.py is created)
streamlit run app.py
```

## Code Style & Tools

- **Formatter:** Ruff (for speed and simplicity)
- **Linter:** Ruff
- **Type Checking:** mypy (to be configured)
- **Testing:** pytest with pytest-cov for coverage
- **Python Version:** 3.10+ (specify in pyproject.toml)

Set up `pyproject.toml` with appropriate tool configurations rather than separate config files.

## Project Structure (to be established)

Expected structure once development begins:
```
finfolio/
├── src/
│   ├── finfolio/          # Main package
│   │   ├── __init__.py
│   │   ├── factchecker.py # Core fact-checking logic
│   │   ├── finance/       # Finance-specific modules
│   │   └── llm/           # LLM integration (if using Claude API)
│   └── app.py             # Streamlit UI entry point (if UI exists)
├── tests/
│   ├── test_factchecker.py
│   └── test_finance.py
├── pyproject.toml         # Dependencies and tool config
├── requirements.txt       # For reproducibility
└── README.md
```

## Model Configuration

If integrating Claude API for fact-checking:
- Use **claude-haiku-4-5-20251001** by default (cheap, fast for finance facts)
- Model name must be a **configuration value** (environment variable or config file), never hardcoded
- Do not change the model in code—configuration only
- `temperature` only if specific need exists; avoid otherwise

## Important Notes for Development

- The .gitignore includes entries for various Python tools—Streamlit, Flask, Django. Clarify which framework is intended once development begins.
- Given the memory constraints on this machine (8GB RAM, 2GB Docker VM), keep dependencies lean. Avoid heavy ML models in memory.
- Since finfolio deals with finance content, ensure fact-checking logic is well-tested and documented for accuracy.
