# Image to Sensor CV - Static Validation

## Quick Start

### Quick Check (No dependencies required)
```bash
./quick-check.sh
```
This performs basic syntax and configuration validation without installing any dependencies.

### Full Validation (Requires dev dependencies)
```bash
./validate.sh
```
This runs comprehensive static analysis including:
- Code formatting (Black)
- Import sorting (isort)
- Linting (Flake8, Pylint)
- Type checking (MyPy)
- Security scanning (Bandit)
- Syntax validation
- Configuration file validation

## Setup

### Install Development Dependencies

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate  # On Windows

# Install all development tools
pip install -r requirements-dev.txt
```

### Individual Tool Usage

#### Format Code (Auto-fix)
```bash
# Format Python files
black *.py

# Sort imports
isort *.py
```

#### Run Linters
```bash
# Flake8
flake8 *.py

# Pylint
pylint *.py
```

#### Type Checking
```bash
# MyPy
mypy *.py
```

#### Security Scan
```bash
# Bandit
bandit -r *.py
```

## VS Code Integration

The `pyproject.toml` file configures all tools with consistent settings. VS Code will automatically use these settings if you have the appropriate extensions installed:

- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- Flake8 (ms-python.flake8)
- MyPy Type Checker (ms-python.mypy-type-checker)

## Configuration Files

- `pyproject.toml` - Central configuration for all Python tools
- `.flake8` - Flake8 specific configuration
- `requirements-dev.txt` - Development dependencies

## Continuous Integration

You can integrate `validate.sh` into your CI/CD pipeline to ensure code quality before deployment:

```yaml
# Example GitHub Actions workflow
- name: Run static validation
  run: |
    cd ha_devel/config/custom_components/image_to_sensor_cv
    ./validate.sh
```

## Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
cd ha_devel/config/custom_components/image_to_sensor_cv
./quick-check.sh
```

Then make it executable:
```bash
chmod +x .git/hooks/pre-commit
```
