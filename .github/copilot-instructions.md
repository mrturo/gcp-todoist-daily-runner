# AI Coding Agent Instructions

## Project Overview
Python 3.11+ FastAPI service for Google Cloud Run that manages Todoist recurring tasks via scheduled HTTP calls. Enforces a structured ticket-naming convention with frequency labels, validates task sequences, and automatically updates overdue recurring tasks.

## Architecture & Data Flow

### Core Flow (See [src/main.py](../src/main.py))
1. **Entry**: `GET /` endpoint (direct HTTP) → `run_todoist_integration()`
2. **Fetch**: Retrieve all tasks via Todoist API ([src/core/processing.py](../src/core/processing.py))
3. **Categorize**: Split into overdue/not-overdue based on current timezone
4. **Update Overdue**: Auto-update recurring daily tasks with `🟢frequency-01-daily` label
5. **Update Next Recurrence**: If `next_recurring_date` is today/past, update due date
6. **Re-categorize**: Refresh task lists after updates
7. **Split**: Separate not-overdue → today vs future tasks
8. **Validate**: Mark duplicated/non-sequential IDs, frequency mismatches
9. **Return**: JSON with `overdue_tasks`, `today_tasks`, `future_tasks`, `issue_tasks`

### Module Structure
- **[src/main.py](../src/main.py)**: FastAPI app, endpoint, API key auth (`X-API-Key` header)
- **[src/core/processing.py](../src/core/processing.py)**: Pure functions (date logic, categorization, title parsing)
- **[src/utils/frequency_labels.py](../src/utils/frequency_labels.py)**: Frequency definitions (5 types: daily→monthly)
- **[src/utils/validators.py](../src/utils/validators.py)**: Ticket-name regex validator
- **[src/run_service.py](../src/run_service.py)**: CLI wrapper for non-server execution (used by `bash envtool.sh run`)

## Critical Patterns

### 1. Ticket Name Convention (Strict Format)
**Required**: `🟢 (A01-02-03) 📝 Task description`

Components validated by [validate_ticket_name](../src/utils/validators.py):
- **Frequency emoji** (`🟢🔵🟡🟠🔴`) - must match assigned frequency label
- **Ticket ID** `([A-Z]##-##-##)` - Area-Category-Task numbering (letter A-Z)
- **Ticket emoji** (any emoji) - task type indicator
- **Description** (≥3 chars after emoji/markdown cleanup)

**Validation Issues Detected**:
- `title.is_complete: false` - missing required components
- `title.duplicated_id: true` - ID used by multiple tasks
- `title.sequential_id: false` - gaps in numbering (e.g., A05 exists but A03 missing)

### 2. Frequency Labels (5 Types)
Defined in [FrequencyLabels](../src/utils/frequency_labels.py) as immutable dataclasses:
```python
DAILY:        🟢frequency-01-daily
MULTIWEEKLY:  🔵frequency-02-multiweekly
WEEKLY:       🟡frequency-03-weekly
MULTIMONTHLY: 🟠frequency-04-multimonthly
MONTHLY:      🔴frequency-05-monthly
```

**Rules**:
- Title emoji must match label emoji (`frequency_matches_label`)
- Must have ≥1 non-frequency label (`has_non_frequency`)

### 3. Date Processing Logic
All timezone handling uses `get_timezone()` ([src/core/processing.py](../src/core/processing.py)):
- Reads `TIME_ZONE` env var (e.g., `America/New_York`)
- Falls back to system timezone if invalid
- **Overdue detection**: Compares task due date to `now(tz)` in local timezone
- **Auto-updates**: Only recurring daily tasks overdue → set due to today
- **Next recurrence**: If `next_recurring_date ≤ today`, update due date to next recurrence

## Development Workflow

### Version Control Policy

**CRITICAL: NO AUTOMATIC GIT COMMITS**
- **NEVER** execute `git commit`, `git add`, `git push`, or any git command that modifies version control state
- **NEVER** use tools like `run_in_terminal` to execute git commands
- **NEVER** create or modify git-related files (e.g., `.gitignore` updates that require commits)
- The user MUST review all changes and commit them manually
- Only create, modify, or delete files as requested - let the user handle version control
- If the user asks about git or commits, remind them they need to commit manually

**Rationale**: The user needs full control over what goes into version control and when. All file changes should be visible in the working directory for the user to review, test, and commit at their discretion.

### Environment Setup ([envtool.sh](../envtool.sh))
```bash
bash envtool.sh install dev    # Create .venv + install deps (requires python3.11)
bash envtool.sh start          # Run FastAPI server (uvicorn on PORT=3001)
bash envtool.sh run            # Direct execution (no server) → saves logs/run_output-*.json
bash envtool.sh test           # pytest with coverage report
bash envtool.sh clean          # Remove __pycache__, .pytest_cache, logs/
bash envtool.sh code-check     # Run code style checks (flake8, black, isort, mypy)
```

**Environment Variables** (`.env` file):
```env
PORT=3001
TIME_ZONE=America/New_York
TODOIST_SECRET_ID=your_token     # Todoist API token
API_KEY=your_secure_key          # Optional: enables X-API-Key auth
```

### Testing Patterns (100% coverage expected)

**Monkeypatching Strategy** ([tests/test_main.py](../tests/test_main.py)):
1. Always patch `main_module.get_todoist_token` → return `"fake-token"`
2. Replace `main_module.TodoistAPI` with fake class containing:
   - `get_tasks()` → return list of mock task objects
   - Mock task objects with `.id`, `.content`, `.due`, `.labels` attributes
   - Due objects expose `.to_dict()` → return `{"date": "...", "recurring": bool}`
3. Use `TestClient(app).get("/")` → validate response JSON structure

**Example Fake API** (common pattern across tests):
```python
class FakeTodoistAPI:
    def __init__(self, token):
        self.token = token
    
    def get_tasks(self):
        return [[SimpleTask(id_="1", content="Task", due=SimpleDue(...))]]
```

**Test Utilities** ([tests/test_utils.py](../tests/test_utils.py)): Shared `SimpleTask`, `SimpleDue` classes

### Code Style & Principles

**Core Principles**:
- Apply **DRY, SOLID, Clean Code, and DDD** principles throughout
- Implement design patterns when appropriate (Factory, Strategy, Adapter, Command, etc.)
- Keep code modular, scalable, secure, and efficient
- Code must be **idempotent and safe for daily automatic executions**
- Prioritize computational and memory efficiency (vectorization, float32, category, joblib, etc.)

**Configuration & Dependencies**:
- Centralize configuration, avoid hardcoded parameters
- Use environment variables for credentials and sensitive configurations
- Dependencies only from [requirements.txt](../requirements.txt) or [requirements-dev.txt](../requirements-dev.txt)
- Never access protected members or use undeclared dependencies

**Naming Conventions**:
- `PascalCase` for classes
- `snake_case` for functions, methods, variables
- `UPPER_SNAKE_CASE` for constants
- Underscore prefix for private helpers (e.g., `_process_due_obj`, `_validate_sequential_id`)
- **All code objects, comments, docstrings in English** (no Spanish in code)

**Language Policy**:
- **Code**: All code, comments, docstrings, and technical documentation MUST be written in English
- **Chat Interactions**: All conversations through GitHub Copilot extension and Copilot CLI MUST be in Spanish
- This applies to responses, explanations, questions, and any conversational output
- Technical terms in conversations can remain in English when appropriate (e.g., "FastAPI", "endpoint", "pytest")

**Code Quality**:
- **Line length**: 100 chars max (not 88/79)
- **Docstrings**: All public functions/classes with detailed descriptions
- **Avoid**: Direct `assert` (raise `AssertionError`), hardcoded configs
- **Testing**: Maintain high test coverage with pytest (expect 100% coverage)
- Code must be directly executable, complete, and functional

**Communication Style**:
- Professional, technical, and direct; no embellishments
- Challenge assumptions to foster learning
- Request clarifications only when necessary for accuracy
- In step-by-step processes, deliver one step per message and wait for confirmation

## Cloud Deployment

**Build & Deploy** ([cloudrun-notes.md](../docs/cloudrun-notes.md)):
```bash
# Build image (from Dockerfile - Python 3.11 slim, non-root user, single worker)
docker build -t gcr.io/<PROJECT_ID>/gcp-todoist-runner .

# Deploy to Cloud Run (optimized for cost: 512Mi, scale-to-zero, 15s timeout)
gcloud run deploy gcp-todoist-runner \
  --image gcr.io/<PROJECT_ID>/gcp-todoist-runner \
  --service-account=todoist-runner-sa@<PROJECT_ID>.iam.gserviceaccount.com \
  --region=<REGION> --memory=512Mi --min-instances=0 --max-instances=1 --timeout=15s
```

## Common Tasks

**Add new frequency type**:
1. Add to [FrequencyLabels](../src/utils/frequency_labels.py) class variables
2. Update `_LABEL_MAP` dict
3. Add tests for label matching in [tests/test_frequency_labels.py](../tests/test_frequency_labels.py)

**Modify ticket validation**:
- Edit regex in [validators.py](../src/utils/validators.py) `_PATTERN`
- Update [test_ticket_name_validator.py](../tests/test_ticket_name_validator.py)

**Change date update logic**:
- Modify [update_overdue_daily_tasks](../src/core/processing.py) or `_update_next_recurrence_due_dates`
- Add test scenarios in [tests/test_main.py](../tests/test_main.py) with monkeypatched timezone/date

**Debug failing tests**:
```bash
pytest -vv tests/test_main.py::test_specific_function  # Run single test
pytest --cov=src --cov-report=html -v tests/           # HTML coverage report → htmlcov/
```

## Key Files Reference
- [README.md](../README.md): Full feature docs, API behavior, quick start
- [Dockerfile](../Dockerfile): Production container config (non-root, slim base)
- [requirements.txt](../requirements.txt): Prod deps (fastapi, todoist-api-python, google-cloud-secret-manager)
- [envtool.sh](../envtool.sh): All dev commands (start/test/clean/run)
- [copilot-project-context.json](../copilot-project-context.json): Code style rules, principles (DRY, SOLID, Clean Code)
