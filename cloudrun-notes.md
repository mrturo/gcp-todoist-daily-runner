
# Quick Deployment on Cloud Run and Cloud Scheduler

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

## 3. Deploy to Cloud Run

```sh
gcloud run deploy gcp-todoist-daily-runner \
  --image gcr.io/<PROJECT_ID>/gcp-todoist-daily-runner \
  --service-account=todoist-runner-sa@<PROJECT_ID>.iam.gserviceaccount.com \
  --region=<REGION> \
  --allow-unauthenticated
```

> You can build and upload the image with Cloud Build or Docker.

## 4. Create a job in Cloud Scheduler

```sh
gcloud scheduler jobs create http daily-todoist-run \
  --schedule="0 6 * * *" \
  --uri="https://<CLOUD_RUN_URL>/" \
  --http-method=GET \
  --time-zone="Europe/Madrid"
```

## Notes

- The secret can have another name; adjust the `TODOIST_SECRET_ID` environment variable if necessary.
- The service is ready to scale to 0 and is stateless.
- Logs can be checked in Cloud Logging.
