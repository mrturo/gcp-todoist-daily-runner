# gcp-todoist-daily-runner

Python service to list all pending tasks from the Todoist API on Google Cloud Run, triggered by Cloud Scheduler or HTTP GET. The Todoist token is obtained from environment variables.

## Description
This service exposes an HTTP endpoint (`/`) that, when invoked (for example, from Cloud Scheduler or a browser), retrieves the Todoist API token from environment variables, initializes the official Todoist client, and returns a list of all active (pending) tasks. It is ready to scale to zero and is stateless.


## Credentials configuration
For local development, credentials (such as the Todoist API token) should be stored in a `.env` file in the project root. Example `.env`:

```env
PORT=3000
TIME_ZONE=time_zone
TODOIST_SECRET_ID=your_todoist_token_here
```

For deployment, credentials should be provided via environment variables in your GitHub Actions workflow configuration.

## Local execution with Docker
```sh
docker build -t gcp-todoist-daily-runner .
docker run -p 3000:3000 \
  -e PORT=3000 \
  -e TIME_ZONE=<time_zone> \
  -e TODOIST_SECRET_ID=<your_todoist_token> \
  -v ~/.config/gcloud:/root/.config/gcloud:ro \
  gcp-todoist-daily-runner
```

> For local testing, make sure you have a valid `.env` file with the required credentials.

## Relevant environment variables
- `PORT`: Listening port (optional, defaults to 3000).
- `TIME_ZONE`: Time Zone (optional, defaults to UTC).
- `TODOIST_SECRET_ID`: Todoist API token (required).

## Consuming from Cloud Scheduler
Cloud Scheduler or any HTTP client should make a GET call to the root endpoint (`/`) of the service deployed on Cloud Run. Example configuration:
- Method: GET
- URL: `https://<CLOUD_RUN_URL>/`

## Project structure
- `src/main.py`: Main FastAPI service code. Lists all pending Todoist tasks.
- `requirements.txt`: Dependencies.
- `Dockerfile`: Image ready for Cloud Run.
- `.gitignore`: Standard exclusions.
- `cloudrun-notes.md`: Quick guide for deployment and infrastructure configuration.

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

# Run code quality checks (black, isort, autoflake, pylint if installed)
bash envtool.sh code-check

# Start the local server (requires .venv and .env configured)
bash envtool.sh start
```

> Requires Python 3.11+ installed as `python3.11` in the system.

For more details, check the `envtool.sh` file itself.

## References
- [Official Todoist API Documentation](https://developer.todoist.com/rest/v2/)
- [Google Cloud Run](https://cloud.google.com/run)