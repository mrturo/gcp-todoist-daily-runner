# gcp-todoist-runner

Python service built with FastAPI that manages and processes recurring tasks from the Todoist API on Google Cloud Run, triggered by HTTP GET. It analyzes task due dates, categorizes overdue/today/future tasks, validates ticket-style task names, manages frequency labels, and automatically updates recurring task dates.

## Description
This service exposes an HTTP endpoint (`/`) that, when invoked (via HTTP client), performs comprehensive Todoist task management:
- Retrieves all pending tasks from Todoist API
- Categorizes tasks into overdue, today, and future groups
- Validates and parses ticket-style task names (format: `🟢 (A01-02-03) 📝 Task description`)
- Manages frequency labels (daily, weekly, monthly, etc.) with emoji indicators
- Automatically updates due dates for overdue recurring tasks
- Detects and flags issues: duplicated IDs, non-sequential IDs, mismatched frequency labels, incomplete titles
- Returns structured JSON with task groups and detected issues

The service is stateless, scales to zero on Cloud Run, and includes API key authentication for production deployments.

## Key Features

### Task Categorization
- **Overdue tasks**: Tasks with due dates in the past
- **Today tasks**: Tasks due today
- **Future tasks**: Tasks due in the future
- Automatic recalculation after updating overdue tasks

### Ticket Name Validation
Validates and parses ticket-style task names with the format:
```
🟢 (A01-02-03) 📝 Task description
```

Components:
- **Frequency emoji** (`🟢`, `🔵`, `🟡`, `🟠`, `🔴`): Indicates recurrence frequency
- **Ticket ID** (`(A01-02-03)`): Structured identifier (Area-Category-Task)
- **Ticket emoji** (`📝`, `🔧`, etc.): Task type indicator
- **Description**: Task details

Detects issues:
- Incomplete titles (missing required components)
- Duplicated IDs across tasks
- Non-sequential IDs (e.g., A05 exists but A03 doesn't)

### Frequency Label Management
Supports five frequency types with corresponding emoji and Todoist labels:
- 🟢 **Daily** (`🟢frequency-01-daily`)
- 🔵 **Multiweekly** (`🔵frequency-02-multiweekly`)
- 🟡 **Weekly** (`🟡frequency-03-weekly`)
- 🟠 **Multimonthly** (`🟠frequency-04-multimonthly`)
- 🔴 **Monthly** (`🔴frequency-05-monthly`)

Validates that:
- Task title emoji matches the assigned frequency label
- Tasks have at least one non-frequency label

### Automatic Due Date Management
- Updates overdue recurring daily tasks to today's date
- Infers next recurrence dates for recurring tasks without explicit `next_recurring_date`
- Supports multiple recurrence patterns: daily, weekly, monthly, specific weekdays
- Updates tasks when next recurrence date has arrived

### Issue Detection and Reporting
The service identifies and reports:
- Tasks with incomplete titles
- Duplicated ticket IDs
- Non-sequential ticket IDs
- Frequency emoji that doesn't match the assigned label
- Tasks missing non-frequency labels

All detected issues are returned in the `issue_tasks` array with detailed descriptions.

## Getting Started

### Prerequisites
- Python 3.11 or higher installed as `python3.11`
- Todoist API token (get it from [Todoist App Settings](https://todoist.com/app/settings/integrations/developer))
- Docker (optional, for containerized execution)
- Google Cloud SDK (optional, for GCP deployment)

### Quick Start - Local Development

1. **Clone the repository**
   ```sh
   git clone <repository_url>
   cd gcp-todoist-runner
   ```

2. **Create a `.env` file** in the project root:
   ```env
   PORT=3001
   TIME_ZONE=America/New_York
   TODOIST_SECRET_ID=your_todoist_token_here
   API_KEY=your_secure_api_key_here
   ```

3. **Install dependencies and set up environment**
   ```sh
   bash envtool.sh install dev
   ```

4. **Run tests to verify setup**
   ```sh
   bash envtool.sh test
   ```

5. **Start the development server**
   ```sh
   bash envtool.sh start
   ```
   
   The service will be available at `http://localhost:3001/`

6. **Or run the service directly (without server)**
   ```sh
   bash envtool.sh run
   ```
   
   Results will be saved to `logs/latest.json`

### Testing the Endpoint

```sh
# Without API key
curl http://localhost:3001/

# With API key (if configured)
curl -H "X-API-Key: your_secure_api_key_here" http://localhost:3001/
```




## Credentials configuration
For local development, credentials (such as the Todoist API token) should be stored in a `.env` file in the project root. Example `.env`:

```env
PORT=3001
TIME_ZONE=time_zone
TODOIST_SECRET_ID=your_todoist_token_here
API_KEY=your_secure_api_key_here
```

For deployment, credentials should be provided via environment variables in your GitHub Actions workflow configuration.

## Local execution with Docker
Build and run the service in a container:

```sh
# Build the image
docker build -t gcp-todoist-runner .

# Run the container
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e TIME_ZONE=America/New_York \
  -e TODOIST_SECRET_ID=<your_todoist_token> \
  -e API_KEY=<your_secure_api_key> \
  gcp-todoist-runner
```

The Dockerfile is optimized for production:
- Uses Python 3.11 Alpine Linux (musl libc, minimal CVEs)
- Runs as non-root user for security
- Installs only production dependencies
- Removes pip and setuptools after installation to reduce attack surface
- Configured for Cloud Run with dynamic port binding (defaults to 8080)
- Smaller image size (~50MB vs ~150MB with Debian)

> For local testing without Docker, use `bash envtool.sh start` with a `.env` file configured.

## Relevant environment variables
- `PORT`: Listening port (optional, defaults to 3001 locally, 8080 on Cloud Run).
- `TIME_ZONE`: Time zone for date processing (optional, defaults to system local timezone or UTC).
- `TODOIST_SECRET_ID`: Todoist API token (required). Get it from [Todoist App Settings](https://todoist.com/app/settings/integrations/developer).
- `API_KEY`: API key for endpoint authentication (optional but strongly recommended for production).
- `OUTPUT_JSON_FILE`: Path to save execution results when using `run_service.py` (optional, defaults to timestamped file in `logs/`).

## Consuming
Any HTTP client should make a GET call to the root endpoint (`/`) of the service deployed on Cloud Run. Example configuration:
- Method: GET
- URL: `https://<CLOUD_RUN_URL>/`
- Header: `X-API-Key: your_api_key_here` (if API_KEY is configured)

### Response format
The service returns a JSON response with the following structure:
```json
{
  "status": "ok",
  "overdue_tasks": [...],
  "today_tasks": [...],
  "future_tasks": [...],
  "issue_tasks": [
    {
      "task_id": "12345",
      "issues": [
        "title is incomplete",
        "frequency emoji does not match label"
      ]
    }
  ]
}
```

Each task includes:
- Standard Todoist fields: `id`, `content`, `labels`, `due`, etc.
- Enhanced fields:
  - `title`: Parsed ticket-style name with `parts` (id, text, emoji), validation flags
  - `frequency_labels`: Frequency detection and validation results
  - Flags: `duplicated_id`, `sequential_id`, `to_replace` (for automatic title corrections)

## Project structure
- `src/main.py`: FastAPI application with endpoint routing and API key authentication
- `src/core/processing.py`: Core business logic for task processing, categorization, and date management
- `src/run_service.py`: Command-line runner for direct execution without starting a server
- `src/utils/frequency_labels.py`: Frequency label definitions with emoji and naming conventions
- `src/utils/validators.py`: Ticket name validation and parsing utilities
- `tests/`: Comprehensive test suite with 30+ test files covering all functionality
- `requirements.txt`: Production dependencies
- `requirements-dev.txt`: Development dependencies (pytest, pytest-cov)
- `Dockerfile`: Production-ready image optimized for Cloud Run
- `envtool.sh`: Development environment management script
- `docs/cloudrun-notes.md`: Deployment guide with cost optimization strategies
- `logs/`: Output directory for execution results (timestamped JSON files)
- `.gitignore`: Standard Python exclusions and project-specific patterns

## Project environment management (`envtool.sh`)

The `envtool.sh` script helps manage the development environment and common project tasks. Main commands:

```sh
# Install dependencies and create the virtual environment (.venv)
bash envtool.sh install dev   # For development
bash envtool.sh install prod  # Only production dependencies

# Reinstall the environment from scratch (removes and recreates .venv)
bash envtool.sh reinstall dev
bash envtool.sh reinstall prod

# Remove the virtual environment (.venv) and caches
bash envtool.sh uninstall
bash envtool.sh clean-env     # Only removes .venv
bash envtool.sh clean-cache   # Only removes caches and artifacts

# Check environment status
bash envtool.sh status

# Run unit tests
bash envtool.sh test

# Run code quality checks + vulnerability scan
# Includes: black, isort, autoflake, pylint, mypy, trivy
# Trivy will build Docker image and scan for vulnerabilities (CRITICAL/HIGH/MEDIUM)
bash envtool.sh code-check

# Skip Docker build if Rancher is slow to start (faster execution)
SKIP_DOCKER_BUILD=true bash envtool.sh code-check

# Start the local server (requires .venv and .env configured)
bash envtool.sh start

# Run the service directly without starting a server (requires .venv and .env configured)
bash envtool.sh run
```

### Difference between `start` and `run`
- **`start`**: Starts a uvicorn server that exposes the service on an HTTP endpoint. Useful for local development and testing via browser or HTTP clients.
- **`run`**: Executes the Todoist integration service directly from the terminal without starting a server. Runs the logic once and displays the result immediately.

> Requires Python 3.11+ installed as `python3.11` in the system.

For more details, check the `envtool.sh` file itself.

## Testing

The project includes comprehensive test coverage with 30+ test files:

```sh
# Run all tests with coverage report
bash envtool.sh test

# Or manually with pytest
source .venv/bin/activate
pytest --cov=src --cov-report=term-missing -v tests/
```

### Test Coverage Areas
- Task fetching and categorization
- Ticket name validation and parsing
- Frequency label detection and validation
- Due date processing and updates
- Overdue task handling
- Recurrence date inference
- Timezone handling and fallbacks
- Sequential ID validation
- Duplicate ID detection
- Error handling and edge cases
- API key authentication
- Direct service execution (`run_service.py`)

Test files are organized by feature and follow naming convention `test_*.py`.

### Security & Vulnerability Testing

The project includes comprehensive vulnerability management with Trivy integration:

**Integrated workflow (recommended)**:
```sh
# Run all quality checks including vulnerability scanning
# Automatically builds Docker image and scans with Trivy
bash envtool.sh code-check
```

**Standalone vulnerability scanning**:
```sh
# Install Trivy (one-time setup)
brew install aquasecurity/trivy/trivy

# Run standalone scan (Alpine Linux = 0 vulnerabilities)
# Automatically builds image if Docker/Rancher is running
bash scripts/local-trivy-test.sh

# Manual image scan
docker build -t gcp-todoist-runner:test .
trivy image --severity CRITICAL,HIGH,MEDIUM gcp-todoist-runner:test
```

**Key features**:
- Alpine Linux base image (python:3.11-alpine) with musl libc
- **0 vulnerabilities** at all severity levels (no .trivyignore filtering needed)
- Automatic Docker/Rancher Desktop detection
- Scans both Dockerfile configuration AND actual built image
- Smaller image size (~50MB vs ~150MB with Debian)


## Output and Logging

### Server Mode (`bash envtool.sh start`)
- Starts a uvicorn server on the configured PORT
- Returns JSON responses via HTTP endpoint
- Logs to stdout (visible in Cloud Run logs or terminal)

### Direct Execution Mode (`bash envtool.sh run`)
- Runs the service logic once without starting a server
- Saves results to `logs/run_output-YYYYMMDD_HHMMSS.json` (timestamped)
- Creates a copy at `logs/latest.json` for quick access
- Supports automatic title updates when `to_replace` flag is detected
- Useful for local testing and debugging

### Log Files
- `logs/latest.json`: Most recent execution result
- `logs/run_output-*.json`: Historical execution results with timestamps
- Log directory is created automatically and excluded from git

## Dependencies

### Production Dependencies
- `fastapi`: Web framework for API endpoints
- `uvicorn[standard]`: ASGI server for FastAPI
- `google-cloud-secret-manager`: GCP Secret Manager integration (optional)
- `todoist-api-python`: Official Todoist API client
- `httpx`: Async HTTP client
- `python-dotenv`: Environment variable management from `.env` files
- `python-dateutil`: Advanced date parsing and manipulation

### Development Dependencies
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting for pytest

## Deployment

### Google Cloud Run Deployment

For detailed deployment instructions including service account setup, cost optimization, see [cloudrun-notes.md](docs/cloudrun-notes.md).

Quick deployment summary:
1. Build and push Docker image to GCR
2. Create service account with Secret Manager access
3. Deploy to Cloud Run with optimized settings (512Mi RAM, scale to zero)

### Cost Optimization

This repository implements aggressive cost-reduction measures to minimize GCP charges:

- **Artifact Registry Vulnerability Scanning**: Automatically disabled during CI/CD (saves ~$5/month)
- **Trivy Local Scanning**: Free vulnerability scanning runs in GitHub Actions before image push
- **Bounded Image Tags**: Short SHA tags (7 chars) reduce registry storage costs
- **Cloud Run Scale-to-Zero**: Service scales down to 0 instances when idle ($0 compute charges)

**Estimated monthly cost**: ~$0.50 (storage only) vs $6-10 without optimization.

For detailed cost analysis, rollback instructions, and additional optimization tips, see [docs/COST_OPTIMIZATION.md](docs/COST_OPTIMIZATION.md)

### Environment Configuration

**Local Development**: Use `.env` file (see Getting Started section)

**Cloud Run Deployment**: Set environment variables in Cloud Run service configuration:
```sh
gcloud run services update gcp-todoist-runner \
  --set-env-vars="TIME_ZONE=America/New_York,API_KEY=your_key_here" \
  --update-secrets=TODOIST_SECRET_ID=todoist-api-token:latest
```

## Troubleshooting

### Common Issues

**Issue**: `TODOIST_SECRET_ID not found in environment variables`
- **Solution**: Ensure `.env` file exists and contains `TODOIST_SECRET_ID=your_token`
- For Cloud Run: verify secret is properly configured and service account has `secretmanager.secretAccessor` role

**Issue**: `Invalid TIME_ZONE, falling back to system local`
- **Solution**: Use valid IANA timezone names (e.g., `America/New_York`, `Europe/Madrid`, `UTC`)

**Issue**: `Port already in use` when running `bash envtool.sh start`
- **Solution**: The script automatically kills processes on the configured port, but you can manually free it:
  ```sh
  lsof -ti :3001 | xargs kill -9
  ```

**Issue**: Tests failing with import errors
- **Solution**: Ensure virtual environment is activated and dev dependencies are installed:
  ```sh
  bash envtool.sh reinstall dev
  ```

**Issue**: `401` or `403` error when calling endpoint
- **Solution**: Include `X-API-Key` header if `API_KEY` environment variable is configured
- Or remove `API_KEY` from environment for development without authentication

### Debug Mode

Enable detailed logging by modifying the uvicorn command in [src/main.py](src/main.py#L322):
```python
uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True, log_level="debug")
```

## Contributing

1. Follow Python best practices (PEP8)
2. Maintain code coverage above 90%
3. Use type hints for function parameters and returns
4. Write comprehensive tests for new features
5. Update documentation when adding features
6. All code, comments, and documentation must be in English

See [copilot-project-context.json](copilot-project-context.json) for detailed coding standards.

## License

See [LICENSE](LICENSE) file for details.

## References
- [Official Todoist API Documentation](https://developer.todoist.com/rest/v2/)
- [Google Cloud Run](https://cloud.google.com/run)