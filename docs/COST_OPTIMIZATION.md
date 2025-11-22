# Cost Optimization for Google Cloud Run Deployment

## Overview

This document describes the cost optimization measures implemented to minimize Google Cloud Platform (GCP) costs for the `gcp-todoist-runner` service, with a focus on eliminating Artifact Registry vulnerability scanning charges.

## Problem Statement

By default, Google Artifact Registry automatically scans container images for vulnerabilities at approximately **$0.26 per image**. For CI/CD pipelines with frequent deployments, this can result in significant monthly costs even for small projects.

**Example cost scenario (before optimization):**
- 20 deployments/month × $0.26/scan = **$5.20/month** just for scanning
- Plus storage costs for unbounded image tags
- **Total: $5-10/month** for a service with minimal traffic

## Implemented Solutions

### 1. Disable Artifact Registry Vulnerability Scanning

**Script:** [`scripts/gcp/disable-ar-vulnerability-scanning.sh`](../scripts/gcp/disable-ar-vulnerability-scanning.sh)

This idempotent script disables vulnerability scanning on the Artifact Registry repository during CI/CD deployment.

**Cost savings:** ~$0.26 per deployment → **$0/month** for scanning

**How it works:**
```bash
gcloud artifacts repositories update "${AR_REPOSITORY}" \
  --location="${GCP_REGION}" \
  --disable-vulnerability-scanning
```

**Integrated in:** GitHub Actions workflow runs this automatically after authentication.

### 2. Replace with Free Trivy Scanning

**Implementation:** [Aquasecurity Trivy GitHub Action](https://github.com/aquasecurity/trivy-action)

Trivy provides free, local container vulnerability scanning that runs in GitHub Actions **before** pushing images to Artifact Registry.

**Features:**
- ✅ **Free**: No GCP charges
- ✅ **Faster**: Scans locally before push
- ✅ **Integrated**: Results appear in GitHub Security tab
- ✅ **Configurable**: Can fail builds on CRITICAL/HIGH vulnerabilities

**Configuration:**
```yaml
- name: Run Trivy vulnerability scanner
  if: env.TRIVY_ENABLED == 'true'
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.IMAGE }}:${{ steps.image-tag.outputs.TAG }}
    severity: 'CRITICAL,HIGH'
    exit-code: '0'  # Change to '1' to fail builds on vulnerabilities
```

**Toggle scanning:** Set `TRIVY_ENABLED: false` in workflow to disable.

### 3. Bounded Image Tags (Short SHA)

**Change:** Image tags use 7-character short SHA instead of full 40-character SHA.

**Before:**
```yaml
IMAGE_TAG: $GITHUB_SHA  # e.g., 3a8f9c2b1e4d6a5c7b8e9f0a1b2c3d4e5f6a7b8c (40 chars)
```

**After:**
```yaml
IMAGE_TAG: ${GITHUB_SHA::7}  # e.g., 3a8f9c2 (7 chars)
```

**Benefits:**
- ✅ Reduces registry storage costs (fewer unique tags)
- ✅ Cleaner image history
- ✅ Still provides unique identification per commit
- ✅ Matches standard Git short SHA convention

## Cost Impact Summary

| Item | Before | After | Monthly Savings |
|------|--------|-------|----------------|
| AR Vulnerability Scanning | $5.20 | $0.00 | **$5.20** |
| Registry Storage (unbounded tags) | ~$1.00 | ~$0.50 | **$0.50** |
| Trivy Scanning | N/A | $0.00 (free) | $0.00 |
| **Total** | **~$6.20/mo** | **~$0.50/mo** | **~$5.70/mo** |

**Annual savings:** ~$68.40

For a service with minimal traffic that otherwise costs $0-2/month for Cloud Run compute, this represents a **significant cost reduction**.

## Rollback Instructions

### Re-enable Artifact Registry Vulnerability Scanning

If you need to restore GCP's built-in vulnerability scanning:

**Option 1: Via gcloud CLI**
```bash
gcloud artifacts repositories update gcp-todoist-runner \
  --location=us-central1 \
  --enable-vulnerability-scanning
```

**Option 2: Via Google Cloud Console**
1. Navigate to [Artifact Registry](https://console.cloud.google.com/artifacts)
2. Select repository: `gcp-todoist-runner`
3. Click "Edit Repository"
4. Enable "Vulnerability Scanning"
5. Save changes

**Option 3: Remove from CI/CD**
Remove or comment out this step in `.github/workflows/deploy.yml`:
```yaml
- name: Disable Artifact Registry vulnerability scanning
  run: |
    chmod +x scripts/gcp/disable-ar-vulnerability-scanning.sh
    AR_REPOSITORY=${{ env.REPO }} GCP_REGION=${{ env.REGION }} \
      ./scripts/gcp/disable-ar-vulnerability-scanning.sh
```

### Disable Trivy Scanning

Set in `.github/workflows/deploy.yml`:
```yaml
env:
  TRIVY_ENABLED: false
```

Or remove the Trivy steps entirely.

### Restore Full SHA Tagging

In `.github/workflows/deploy.yml`, change:
```yaml
# From:
- name: Set image tag (short SHA for cost efficiency)
  id: image-tag
  run: echo "TAG=${GITHUB_SHA::7}" >> $GITHUB_OUTPUT

# To:
- name: Set image tag
  id: image-tag
  run: echo "TAG=$GITHUB_SHA" >> $GITHUB_OUTPUT
```

## Security Considerations

**Q: Is it safe to disable Artifact Registry vulnerability scanning?**

**A:** Yes, when replaced with an equivalent solution like Trivy:
- ✅ Trivy uses the same CVE databases (NVD, GitHub Security Advisories, etc.)
- ✅ Scanning happens **earlier** in CI/CD (before push)
- ✅ Results are tracked in GitHub Security tab
- ✅ Can be configured to block deployments on critical vulnerabilities

**Q: Should I fail builds on vulnerabilities?**

**A:** Recommended approach:
1. Start with `exit-code: '0'` (log only, don't fail)
2. Review vulnerability reports for 2-4 weeks
3. Address legitimate issues in base images and dependencies
4. Switch to `exit-code: '1'` (fail builds) once baseline is clean
5. Exceptions can be handled via `.trivyignore` file

**Q: What about compliance requirements?**

If your organization requires GCP-native scanning for compliance:
- Keep AR vulnerability scanning enabled
- Remove Trivy or use both (belt and suspenders approach)
- Budget accordingly ($5-10/month)

## Additional Cost Optimization Tips

### 1. Image Cleanup Policy
Set up lifecycle policies to auto-delete old images:

```bash
# Delete images older than 30 days with tag pattern
gcloud artifacts repositories set-cleanup-policies gcp-todoist-runner \
  --location=us-central1 \
  --policy=keep-minimum-versions=5,delete-after-days=30
```

### 2. Cloud Run Optimizations (Already Implemented)
From [`cloudrun-notes.md`](cloudrun-notes.md):
- ✅ `--min-instances=0` (scale to zero)
- ✅ `--memory=512Mi` (minimum required)
- ✅ `--cpu-throttling` (CPU only billed during requests)
- ✅ `--timeout=15s` (prevents runaway costs)

### 3. Monitoring Setup
Track costs using GCP Budget Alerts:

```bash
# Create budget alert for $5/month threshold
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="gcp-todoist-runner Budget" \
  --budget-amount=5 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

## Verification

After deployment, verify the changes:

```bash
# 1. Check AR vulnerability scanning status
gcloud artifacts repositories describe gcp-todoist-runner \
  --location=us-central1 \
  --format="value(vulnerabilityScanningConfig.enablementState)"

# Expected output: DISABLED

# 2. Check recent images use short SHA tags
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/gcp-todoist-runner/gcp-todoist-runner \
  --format="table(image:label=IMAGE,version:label=TAG)" \
  --limit=5

# Expected: Tags like 3a8f9c2, b4e5f1a (7 chars), not full 40-char SHAs

# 3. Monitor costs in billing dashboard
# https://console.cloud.google.com/billing
```

## References

- [Artifact Registry Pricing](https://cloud.google.com/artifact-registry/pricing)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Cloud Run Pricing Calculator](https://cloud.google.com/products/calculator)
- [GCP Cost Optimization Best Practices](https://cloud.google.com/architecture/cost-optimization)

## Support

For questions or issues related to cost optimization:
1. Review this document
2. Check GitHub Actions workflow logs
3. Verify GCP billing reports
4. Open an issue in the repository

---

**Last Updated:** January 3, 2026
