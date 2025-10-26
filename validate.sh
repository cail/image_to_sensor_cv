#!/bin/bash
# Static validation script for image_to_sensor_cv
# This script runs all static checks without starting Home Assistant
#
# Usage:
#   ./validate.sh              - Run all checks
#   ./validate.sh black        - Run only black formatting check
#   ./validate.sh isort        - Run only isort check
#   ./validate.sh flake8       - Run only flake8 linting
#   ./validate.sh pylint       - Run only pylint
#   ./validate.sh mypy         - Run only mypy type checking
#   ./validate.sh bandit       - Run only bandit security check
#   ./validate.sh syntax       - Run only syntax check
#   ./validate.sh manifest     - Run only manifest.json validation
#   ./validate.sh common       - Run only common issues check
#   ./validate.sh setup        - Only setup environment (no checks)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Track if any check fails
FAILED=0

# Setup function
setup_environment() {
    if [ "${SKIP_SETUP}" = "1" ]; then
        return 0
    fi
    
    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
        python3 -m venv .venv
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    fi

    # Activate virtual environment
    if [ -z "${VIRTUAL_ENV}" ]; then
        echo -e "${BLUE}Activating virtual environment...${NC}"
        source .venv/bin/activate
    fi

    # Install/update dependencies
    echo -e "${BLUE}Installing dependencies...${NC}"
    pip install -q --upgrade pip
    pip install -q -r requirements-dev.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
    echo ""
}

# Individual checker functions

check_black() {
    echo -e "${BLUE}Running Black formatting check...${NC}"
    if black --check --diff *.py 2>&1 | head -50; black --check *.py; then
        echo -e "${GREEN}✓ Black formatting check passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Black formatting check failed${NC}"
        echo -e "${YELLOW}Run 'black *.py' to auto-fix${NC}"
        return 1
    fi
}

check_isort() {
    echo -e "${BLUE}Running Import sorting check (isort)...${NC}"
    if isort --check-only --diff *.py 2>&1 | head -50; isort --check-only *.py; then
        echo -e "${GREEN}✓ Import sorting check passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Import sorting check failed${NC}"
        echo -e "${YELLOW}Run 'isort *.py' to auto-fix${NC}"
        return 1
    fi
}

check_flake8() {
    echo -e "${BLUE}Running Flake8 linting...${NC}"
    if flake8 *.py; then
        echo -e "${GREEN}✓ Flake8 linting passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Flake8 linting failed${NC}"
        return 1
    fi
}

check_pylint() {
    echo -e "${BLUE}Running Pylint...${NC}"
    pylint *.py --exit-zero > .pylint_report.txt
    PYLINT_SCORE=$(grep "Your code has been rated" .pylint_report.txt | awk '{print $7}' | cut -d'/' -f1 || echo "0")
    echo -e "Pylint score: ${YELLOW}${PYLINT_SCORE}/10${NC}"
    
    if (( $(echo "$PYLINT_SCORE < 7.0" | bc -l) )); then
        echo -e "${YELLOW}⚠ Pylint score is below 7.0 (current: ${PYLINT_SCORE})${NC}"
        echo "Top issues:"
        grep -A 3 "************* Module" .pylint_report.txt | head -20
        return 1
    else
        echo -e "${GREEN}✓ Pylint check passed (score: ${PYLINT_SCORE})${NC}"
        return 0
    fi
}

check_mypy() {
    echo -e "${BLUE}Running MyPy type checking...${NC}"
    if mypy *.py --no-error-summary 2>&1 | tee .mypy_report.txt; then
        ERROR_COUNT=$(grep -c "error:" .mypy_report.txt 2>/dev/null || echo "0")
        if [ "$ERROR_COUNT" -eq "0" ]; then
            echo -e "${GREEN}✓ MyPy type checking passed${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ Found $ERROR_COUNT type errors${NC}"
            cat .mypy_report.txt
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ MyPy found type issues (see above)${NC}"
        return 1
    fi
}

check_bandit() {
    echo -e "${BLUE}Running Security check (Bandit)...${NC}"
    bandit -r *.py -f txt -o .bandit_report.txt 2>/dev/null
    cat .bandit_report.txt
    
    if grep -q "Severity: High" .bandit_report.txt 2>/dev/null; then
        echo -e "${RED}✗ Security check failed (High severity issues found)${NC}"
        return 1
    else
        echo -e "${GREEN}✓ Security check passed${NC}"
        return 0
    fi
}

check_syntax() {
    echo -e "${BLUE}Running Python syntax check...${NC}"
    local SYNTAX_ERRORS=0
    
    for file in *.py; do
        if ! python -m py_compile "$file" 2>/dev/null; then
            echo -e "${RED}✗ Syntax error in $file${NC}"
            python -m py_compile "$file"
            SYNTAX_ERRORS=1
        fi
    done

    if [ $SYNTAX_ERRORS -eq 0 ]; then
        echo -e "${GREEN}✓ All Python files have valid syntax${NC}"
        return 0
    else
        echo -e "${RED}✗ Syntax errors found${NC}"
        return 1
    fi
}

check_manifest() {
    echo -e "${BLUE}Validating manifest.json...${NC}"
    if python -c "import json; json.load(open('manifest.json'))" 2>/dev/null; then
        echo -e "${GREEN}✓ manifest.json is valid${NC}"
        return 0
    else
        echo -e "${RED}✗ manifest.json is invalid${NC}"
        python -c "import json; json.load(open('manifest.json'))"
        return 1
    fi
}

check_common() {
    echo -e "${BLUE}Checking for common issues...${NC}"
    local COMMON_ISSUES=0

    # Check for print statements (should use logging)
    if grep -n "print(" *.py 2>/dev/null | grep -v "# noqa" | grep -v test_ | grep -v "debug"; then
        echo -e "${YELLOW}⚠ Found print() statements. Consider using logging instead.${NC}"
        COMMON_ISSUES=1
    fi

    # Check for TODO/FIXME comments
    if grep -n "TODO\|FIXME" *.py 2>/dev/null; then
        echo -e "${YELLOW}⚠ Found TODO/FIXME comments${NC}"
    fi

    if [ $COMMON_ISSUES -eq 0 ]; then
        echo -e "${GREEN}✓ No common issues found${NC}"
        return 0
    else
        return 1
    fi
}

# Main execution logic
main() {
    local CHECK_TO_RUN="$1"
    
    # Special case for setup only
    if [ "$CHECK_TO_RUN" = "setup" ]; then
        echo -e "${BLUE}=====================================${NC}"
        echo -e "${BLUE}Setting up environment only${NC}"
        echo -e "${BLUE}=====================================${NC}"
        echo ""
        setup_environment
        echo -e "${GREEN}✓ Environment setup complete${NC}"
        exit 0
    fi
    
    # Setup environment for all other checks
    setup_environment
    
    # Run specific check or all checks
    case "$CHECK_TO_RUN" in
        black)
            check_black
            exit $?
            ;;
        isort)
            check_isort
            exit $?
            ;;
        flake8)
            check_flake8
            exit $?
            ;;
        pylint)
            check_pylint
            exit $?
            ;;
        mypy)
            check_mypy
            exit $?
            ;;
        bandit)
            check_bandit
            exit $?
            ;;
        syntax)
            check_syntax
            exit $?
            ;;
        manifest)
            check_manifest
            exit $?
            ;;
        common)
            check_common
            exit $?
            ;;
        "")
            # Run all checks
            echo -e "${BLUE}=====================================${NC}"
            echo -e "${BLUE}Image to Sensor CV - Static Validation${NC}"
            echo -e "${BLUE}=====================================${NC}"
            echo ""
            
            check_black || FAILED=1
            echo ""
            
            check_isort || FAILED=1
            echo ""
            
            check_flake8 || FAILED=1
            echo ""
            
            check_pylint || FAILED=1
            echo ""
            
            check_mypy || FAILED=1
            echo ""
            
            check_bandit || FAILED=1
            echo ""
            
            check_syntax || FAILED=1
            echo ""
            
            check_manifest || FAILED=1
            echo ""
            
            check_common || FAILED=1
            echo ""
            
            # Summary
            echo -e "${BLUE}=====================================${NC}"
            echo -e "${BLUE}Validation Summary${NC}"
            echo -e "${BLUE}=====================================${NC}"

            if [ $FAILED -eq 0 ]; then
                echo -e "${GREEN}✓ All checks passed!${NC}"
                echo -e "${GREEN}Your code is ready for deployment.${NC}"
                exit 0
            else
                echo -e "${RED}✗ Some checks failed.${NC}"
                echo -e "${YELLOW}Please fix the issues above before deployment.${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}Unknown check: $CHECK_TO_RUN${NC}"
            echo ""
            echo "Usage: $0 [check]"
            echo ""
            echo "Available checks:"
            echo "  black      - Code formatting check"
            echo "  isort      - Import sorting check"
            echo "  flake8     - Linting check"
            echo "  pylint     - Advanced linting with score"
            echo "  mypy       - Type checking"
            echo "  bandit     - Security check"
            echo "  syntax     - Python syntax validation"
            echo "  manifest   - manifest.json validation"
            echo "  common     - Common issues check"
            echo "  setup      - Setup environment only"
            echo ""
            echo "Run without arguments to execute all checks"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
