function start_project() {
    if [ ! -d ".venv" ]; then
        echo -e "${RED}❌ The virtual environment (.venv) does not exist. Run first: bash envtool.sh install dev${NC}"
        exit 1
    fi
    echo -e "${GREEN}🚀 Starting the server for local development...${NC}"
    source .venv/bin/activate
    # Load variables from .env if it exists
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    fi
    export PORT="${port:-${PORT:-3001}}"
    export TIME_ZONE="${time_zone:-${TIME_ZONE:-}}"
    export TODOIST_SECRET_ID="${todoist_secret_id:-${TODOIST_SECRET_ID:-}}"
    # Where to save the JSON result when running the service.
    # Default: logs/run_output-YYYYMMDD_HHMMSS.json (unique per run)
    mkdir -p logs
    export OUTPUT_JSON_FILE="${output_json_file:-${OUTPUT_JSON_FILE:-logs/run_output-$(date +%Y%m%d_%H%M%S).json}}"

    # Force free the port before starting
    if lsof -ti :$PORT >/dev/null; then
        echo -e "${RED}⚠️  Port $PORT is in use. Killing process...${NC}"
        lsof -ti :$PORT | xargs kill -9 || true
    fi

    uvicorn src.main:app --host 0.0.0.0 --port $PORT
    deactivate
}

function run_service() {
    if [ ! -d ".venv" ]; then
        echo -e "${RED}❌ The virtual environment (.venv) does not exist. Run first: bash envtool.sh install dev/prod${NC}"
        exit 1
    fi
    echo -e "${GREEN}🏃 Running the Todoist integration service directly...${NC}"
    source .venv/bin/activate
    # Load variables from .env if it exists
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    fi
    export TIME_ZONE="${time_zone:-$TIME_ZONE}"
    export TODOIST_SECRET_ID="${todoist_secret_id:-$TODOIST_SECRET_ID}"

    # Ensure logs dir and default output file (timestamped)
    mkdir -p logs
    export OUTPUT_JSON_FILE="${output_json_file:-${OUTPUT_JSON_FILE:-logs/run_output-$(date +%Y%m%d_%H%M%S).json}}"

    # Run as a module so `src` package imports resolve correctly from project root
    python -m src.run_service
    local status=$?
    deactivate
    if [ $status -eq 0 ]; then
        echo -e "${GREEN}✅ Service completed successfully.${NC}"
        # If the service wrote the timestamped file, also update logs/latest.json
        if [ -n "${OUTPUT_JSON_FILE:-}" ] && [ -f "${OUTPUT_JSON_FILE}" ]; then
            cp -f "${OUTPUT_JSON_FILE}" logs/latest.json || true
            echo -e "${GREEN}📄 Also saved latest copy to logs/latest.json${NC}"
        else
            echo -e "${RED}⚠️  Output file not found: ${OUTPUT_JSON_FILE}${NC}"
        fi
    else
        echo -e "${RED}❌ Service failed. Check the log above.${NC}"
        exit $status
    fi
}

function run_tests() {
    if [ ! -d ".venv" ]; then
        echo -e "${RED}❌ The virtual environment (.venv) does not exist. Run first: bash envtool.sh install dev${NC}"
        exit 1
    fi
    echo -e "${GREEN}🪪 Running unit tests...${NC}"
    source .venv/bin/activate
    pytest --cov=src --cov-report=term-missing -v tests/
    local status=$?
    deactivate
    if [ $status -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed successfully.${NC}"
    else
        echo -e "${RED}❌ Some tests failed. Check the log above.${NC}"
        exit $status
    fi
}
#!/bin/bash

set -euo pipefail
cd "$(dirname "$0")"

# Color formatting
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color


 # Reused functions from envtool_base.sh adapted for this project
function clean_cache() {
    echo -e "${GREEN}🧹 Cleaning project cache and artifacts...${NC}"
    find . -type d -name "__pycache__" -exec rm -rf {} +
    rm -rf .pytest_cache .mypy_cache .cache dist build *.egg-info htmlcov .coverage
    # Remove logs directory entirely (including latest.json and timestamped runs)
    if [ -d "logs" ]; then
        echo -e "${GREEN}🗑️  Removing logs directory...${NC}"
        rm -rf logs
    fi
    echo -e "${GREEN}✅ Cache and artifacts removed.${NC}"
}

function clean_env() {
    if [ -d ".venv" ]; then
        echo -e "${GREEN}🪨 Removing virtual environment (.venv)...${NC}"
        rm -rf .venv
        echo -e "${GREEN}✅ .venv successfully removed.${NC}"
    else
        echo -e "${GREEN}ℹ️  .venv directory not found. Nothing to remove.${NC}"
    fi
}

function clean_all() {
    clean_cache
    clean_env
}

function code_check() {
    local paths=("src/" "tests/")
    echo -e "${GREEN}📁 Using paths: ${paths[*]}${NC}"
    # Only run if the tools are installed
    if command -v black >/dev/null 2>&1; then
        echo -e "${GREEN}🎨 Running black...${NC}"
        black "${paths[@]}"
    fi
    if command -v isort >/dev/null 2>&1; then
        echo -e "${GREEN}🔧 Running isort...${NC}"
        isort "${paths[@]}"
    fi
    if command -v autoflake >/dev/null 2>&1; then
        echo -e "${GREEN}🧹 Running autoflake...${NC}"
        autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive "${paths[@]}"
    fi
    if command -v pylint >/dev/null 2>&1; then
        echo -e "${GREEN}🔍 Running pylint...${NC}"
        pylint --persistent=no "${paths[@]}"
    fi
    if command -v mypy >/dev/null 2>&1; then
        echo -e "${GREEN}🔬 Running mypy...${NC}"
        mypy "${paths[@]}"
    fi
    
    # Build Docker image with --no-cache before Trivy scan
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🐳 Building Docker image (no cache)${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    docker build --no-cache -t gcp-todoist-runner .

    # Run Trivy vulnerability scan
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🔒 Trivy Vulnerability Scan${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    if ! command -v trivy >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Trivy not installed${NC}"
        echo -e "${YELLOW}   Install with: brew install aquasecurity/trivy/trivy${NC}"
        echo ""
    elif [ ! -f "scripts/local-trivy-test.sh" ]; then
        echo -e "${RED}❌ scripts/local-trivy-test.sh not found${NC}"
        echo ""
    else
        # Run the comprehensive vulnerability scan (exits with error if vulnerabilities found)
        bash scripts/local-trivy-test.sh
        local trivy_status=$?
        if [ $trivy_status -ne 0 ]; then
            echo ""
            echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${RED}❌ Quality Checks Failed: Vulnerabilities Found${NC}"
            echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            exit $trivy_status
        fi
    fi
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Quality Checks Completed${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

function check_status() {
    echo -e "${GREEN}🔎 Checking environment status...${NC}"
    if [ -d ".venv" ]; then
        echo -e "${GREEN}✔️  The virtual environment (.venv) exists.${NC}"
    else
        echo -e "${RED}❌ The virtual environment (.venv) is missing.${NC}"
    fi
    if [ -f "requirements.txt" ]; then
        echo -e "${GREEN}✔️  requirements.txt found.${NC}"
    else
        echo -e "${RED}❌ requirements.txt is missing.${NC}"
    fi
    if [ -x ".venv/bin/python" ]; then
        VENV_PYTHON_VERSION=$(./.venv/bin/python --version 2>&1)
        VENV_PIP_VERSION=$(./.venv/bin/pip --version 2>&1)
        echo -e "${GREEN}🐍 Python in .venv: ${VENV_PYTHON_VERSION}${NC}"
        echo -e "${GREEN}📦 Pip in .venv: ${VENV_PIP_VERSION}${NC}"
    fi
    echo -e "${GREEN}🔚 Status check finished.${NC}"
}

function install() {
    local mode="${1:-dev}"
    local PYTHON_BINARY="${PYTHON_BINARY_OVERRIDE:-python3.11}"
    local REQUIRED_MAJOR=3
    local REQUIRED_MINOR=11

    if [[ "$mode" != "prod" && "$mode" != "dev" ]]; then
        echo -e "${RED}❌ You must specify the installation mode: 'prod' or 'dev'.${NC}"
        echo -e "${RED}   Example: bash envtool.sh install prod${NC}"
        echo -e "${RED}   Example: bash envtool.sh install dev${NC}"
        exit 1
    fi

    echo -e "${GREEN}🚀 Installing Python environment $PYTHON_BINARY...${NC}"
    find . -name '__pycache__' -exec rm -rf {} +

    PY_VERSION=$($PYTHON_BINARY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [ "$PY_MAJOR" -lt "$REQUIRED_MAJOR" ] || { [ "$PY_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$PY_MINOR" -lt "$REQUIRED_MINOR" ]; }; then
        echo -e "${RED}❌ Python >= $REQUIRED_MAJOR.$REQUIRED_MINOR required. Found: $PY_VERSION${NC}"
        exit 1
    fi

    if [ ! -d ".venv" ]; then
        echo -e "${GREEN}📦 Creating virtual environment (.venv) using $PYTHON_BINARY...${NC}"
        $PYTHON_BINARY -m venv .venv
    else
        echo -e "${GREEN}📁 Virtual environment already exists. Skipping creation.${NC}"
    fi

    echo -e "${GREEN}💡 Activating virtual environment...${NC}"
    source .venv/bin/activate

    echo -e "${GREEN}⬆️  Upgrading pip...${NC}"
    pip install --upgrade pip


    if [ -f "requirements.txt" ]; then
        echo -e "${GREEN}📄 Installing dependencies from requirements.txt...${NC}"
        pip install -r requirements.txt
    else
        echo -e "${RED}❌ requirements.txt not found. Please add one.${NC}"
        exit 1
    fi

    if [ "$mode" = "dev" ] && [ -f "requirements-dev.txt" ]; then
        echo -e "${GREEN}📄 Installing dev dependencies from requirements-dev.txt...${NC}"
        pip install -r requirements-dev.txt
    fi

    echo -e "${GREEN}✅ Environment ready. Activate with: source .venv/bin/activate${NC}"
}


unset_proxies() {
    unset HTTP_PROXY
    unset HTTPS_PROXY
    unset http_proxy
    unset https_proxy
}

case "${1:-}" in
    install)
        unset_proxies
        shift
        install "$@"
        ;;
    reinstall)
        unset_proxies
        clean_all
        shift
        install "$@"
        ;;
    uninstall)
        unset_proxies
        clean_all
        ;;
    clean-env)
        unset_proxies
        clean_env
        ;;
    clean-cache)
        unset_proxies
        clean_cache
        ;;
    code-check)
        unset_proxies
        shift
        code_check "$@"
        ;;
    status)
        unset_proxies
        check_status
        ;;
    test)
        unset_proxies
        run_tests
        ;;
    start)
        unset_proxies
        start_project
        ;;
    run)
        unset_proxies
        run_service
        ;;
    *)
        echo -e "${RED}Unsupported command. Use: install [dev|prod], reinstall [dev|prod], uninstall, clean-env, clean-cache, code-check, status, test, start, run${NC}"
        exit 1
        ;;
esac
