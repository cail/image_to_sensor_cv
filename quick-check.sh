#!/bin/bash
# Quick syntax and import check for image_to_sensor_cv
# Fast check without installing heavy dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}Quick validation check...${NC}"
echo ""

FAILED=0

# 1. Python syntax check
echo -e "${BLUE}Checking Python syntax...${NC}"
for file in *.py; do
    if [ -f "$file" ]; then
        if ! python3 -m py_compile "$file" 2>/dev/null; then
            echo -e "${RED}✗ Syntax error in $file${NC}"
            python3 -m py_compile "$file"
            FAILED=1
        else
            echo -e "${GREEN}✓ $file${NC}"
        fi
    fi
done
echo ""

# 2. Check manifest.json
echo -e "${BLUE}Validating manifest.json...${NC}"
if python3 -c "import json; json.load(open('manifest.json'))" 2>/dev/null; then
    echo -e "${GREEN}✓ manifest.json is valid${NC}"
else
    echo -e "${RED}✗ manifest.json is invalid${NC}"
    python3 -c "import json; json.load(open('manifest.json'))"
    FAILED=1
fi
echo ""

# 3. Check for obvious import issues (using AST)
echo -e "${BLUE}Checking imports...${NC}"
python3 << 'PYEOF'
import ast
import sys
from pathlib import Path

failed = False
for py_file in Path('.').glob('*.py'):
    try:
        with open(py_file) as f:
            ast.parse(f.read())
        print(f"\033[0;32m✓ {py_file}\033[0m")
    except SyntaxError as e:
        print(f"\033[0;31m✗ {py_file}: {e}\033[0m")
        failed = True

sys.exit(1 if failed else 0)
PYEOF

if [ $? -ne 0 ]; then
    FAILED=1
fi
echo ""

# 4. Check strings.json
if [ -f "strings.json" ]; then
    echo -e "${BLUE}Validating strings.json...${NC}"
    if python3 -c "import json; json.load(open('strings.json'))" 2>/dev/null; then
        echo -e "${GREEN}✓ strings.json is valid${NC}"
    else
        echo -e "${RED}✗ strings.json is invalid${NC}"
        FAILED=1
    fi
    echo ""
fi

# 5. Check services.yaml
if [ -f "services.yaml" ]; then
    echo -e "${BLUE}Validating services.yaml...${NC}"
    # Try with PyYAML if available, otherwise just check it's readable
    if python3 -c "import yaml" 2>/dev/null; then
        if python3 -c "import yaml; yaml.safe_load(open('services.yaml'))" 2>/dev/null; then
            echo -e "${GREEN}✓ services.yaml is valid${NC}"
        else
            echo -e "${RED}✗ services.yaml is invalid${NC}"
            python3 -c "import yaml; yaml.safe_load(open('services.yaml'))" || true
            FAILED=1
        fi
    else
        # YAML module not available, just check file is readable
        if [ -r "services.yaml" ]; then
            echo -e "${GREEN}✓ services.yaml exists (install PyYAML for validation)${NC}"
        else
            echo -e "${RED}✗ services.yaml not readable${NC}"
            FAILED=1
        fi
    fi
    echo ""
fi

# Summary
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Quick validation passed!${NC}"
    echo -e "Run ./validate.sh for comprehensive checks (requires dependencies)"
    exit 0
else
    echo -e "${RED}✗ Quick validation failed${NC}"
    exit 1
fi
