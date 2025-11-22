
# Quick Deployment on Cloud Run

## 1. Create a dedicated Service Account

```sh
gcloud iam service-accounts create todoist-runner-sa \
  --display-name="Service Account for Cloud Run and Secret Manager"
```

## 2. Grant minimum permissions on the secret

```sh
gcloud secrets add-iam-policy-binding todoist-api-token \
  --member="serviceAccount:todoist-runner-sa@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 3. Deploy to Cloud Run (Optimized for minimum cost)

```sh
gcloud run deploy gcp-todoist-runner \
  --image gcr.io/<PROJECT_ID>/gcp-todoist-runner \
  --service-account=todoist-runner-sa@<PROJECT_ID>.iam.gserviceaccount.com \
  --region=<REGION> \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --timeout=15s \
  --min-instances=0 \
  --max-instances=1 \
  --cpu-throttling \
  --concurrency=10
```

### Applied cost optimizations:
- `--memory=512Mi`: Minimum required memory (reduces GiB-second cost)
- `--cpu=1`: 1 vCPU (sufficient for this workload)
- `--timeout=15s`: Short timeout (your service takes ~2-5s)
- `--min-instances=0`: Scale to zero when no traffic (cost $0 at rest)
- `--max-instances=1`: Limits concurrent instances (prevents unexpected costs)
- `--cpu-throttling`: CPU only active during requests (no CPU charge when idle)
- `--concurrency=10`: Handles multiple requests in one instance

> You can build and upload the image with Cloud Build or Docker.

## Notes

- The secret can have another name; adjust the `TODOIST_SECRET_ID` environment variable if necessary.
- The service is ready to scale to 0 and is stateless.
- Logs can be checked in Cloud Logging.
