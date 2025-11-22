#!/bin/bash
# Validation script for cost optimization changes
# Run this after deploying to verify all optimizations are active

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Validating GCP Cost Optimization Changes..."
echo ""

# Check if required env vars are set
if [ -z "${GCP_PROJECT_ID:-}" ]; then
  echo -e "${YELLOW}⚠️  GCP_PROJECT_ID not set. Using gcloud config...${NC}"
  GCP_PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "${GCP_PROJECT_ID}" ]; then
  echo -e "${RED}❌ ERROR: GCP_PROJECT_ID not found. Please set it or configure gcloud.${NC}"
  exit 1
fi

REGION="${GCP_REGION:-us-central1}"
REPO="${AR_REPOSITORY:-gcp-todoist-runner}"
SERVICE="${SERVICE_NAME:-gcp-todoist-runner}"

echo "Using configuration:"
echo "  Project ID: $GCP_PROJECT_ID"
echo "  Region: $REGION"
echo "  Repository: $REPO"
echo "  Service: $SERVICE"
echo ""

# Test 1: Check if AR vulnerability scanning is disabled
echo "📦 Test 1: Artifact Registry Vulnerability Scanning Status"
SCANNING_STATE=$(gcloud artifacts repositories describe "$REPO" \
  --location="$REGION" \
  --format="value(vulnerabilityScanningConfig.enablementState)" 2>/dev/null || echo "UNKNOWN")

if [ "$SCANNING_STATE" = "DISABLED" ]; then
  echo -e "${GREEN}✅ PASSED: Vulnerability scanning is disabled${NC}"
elif [ "$SCANNING_STATE" = "ENABLED" ]; then
  echo -e "${RED}❌ FAILED: Vulnerability scanning is still enabled${NC}"
  echo "   Run: ./scripts/gcp/disable-ar-vulnerability-scanning.sh"
elif [ "$SCANNING_STATE" = "UNKNOWN" ]; then
  echo -e "${YELLOW}⚠️  WARNING: Could not check scanning status (repository may not exist)${NC}"
else
  echo -e "${YELLOW}⚠️  WARNING: Unknown scanning state: $SCANNING_STATE${NC}"
fi
echo ""

# Test 2: Check if images use short SHA tags
echo "🏷️  Test 2: Image Tagging Strategy (Short SHA)"
IMAGE_TAGS=$(gcloud artifacts docker images list \
  "$REGION-docker.pkg.dev/$GCP_PROJECT_ID/$REPO/$SERVICE" \
  --format="csv[no-heading](version)" \
  --limit=5 2>/dev/null || echo "")

if [ -z "$IMAGE_TAGS" ]; then
  echo -e "${YELLOW}⚠️  WARNING: No images found (repository may be empty)${NC}"
else
  SHORT_SHA_COUNT=$(echo "$IMAGE_TAGS" | grep -E '^[a-f0-9]{7}$' | wc -l | tr -d ' ')
  LONG_SHA_COUNT=$(echo "$IMAGE_TAGS" | grep -E '^[a-f0-9]{40}$' | wc -l | tr -d ' ')
  
  echo "   Recent tags:"
  echo "$IMAGE_TAGS" | head -3 | sed 's/^/     - /'
  
  if [ "$SHORT_SHA_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ PASSED: Found $SHORT_SHA_COUNT image(s) with short SHA tags${NC}"
  else
    echo -e "${YELLOW}⚠️  INFO: No short SHA tags found yet (deploy may not have run)${NC}"
  fi
  
  if [ "$LONG_SHA_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}   Note: Found $LONG_SHA_COUNT old image(s) with full SHA tags (will be cleaned up over time)${NC}"
  fi
fi
echo ""

# Test 3: Check Cloud Run service is running
echo "🚀 Test 3: Cloud Run Service Status"
SERVICE_URL=$(gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --format="value(status.url)" 2>/dev/null || echo "")

if [ -n "$SERVICE_URL" ]; then
  echo -e "${GREEN}✅ PASSED: Service is deployed and running${NC}"
  echo "   URL: $SERVICE_URL"
  
  # Optional: Test endpoint if API_KEY is not required or provided
  if [ -n "${API_KEY:-}" ]; then
    echo "   Testing endpoint with API key..."
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "X-API-Key: $API_KEY" \
      "$SERVICE_URL" || echo "000")
    if [ "$HTTP_STATUS" = "200" ]; then
      echo -e "${GREEN}   ✅ Endpoint responding successfully${NC}"
    else
      echo -e "${YELLOW}   ⚠️  Endpoint returned HTTP $HTTP_STATUS${NC}"
    fi
  fi
else
  echo -e "${RED}❌ FAILED: Cloud Run service not found${NC}"
  echo "   Check if deployment succeeded in GitHub Actions"
fi
echo ""

# Test 4: Estimate monthly costs
echo "💰 Test 4: Cost Estimation"
echo "   Artifact Registry vulnerability scanning: $0.00 (disabled)"
echo "   Image storage (estimated): ~$0.50/month"
echo "   Cloud Run compute (scale-to-zero): $0.00 when idle"
echo -e "${GREEN}   Estimated total: ~$0.50/month${NC}"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$SCANNING_STATE" = "DISABLED" ] && [ -n "$SERVICE_URL" ]; then
  echo -e "${GREEN}✅ All critical checks passed!${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. Monitor GitHub Security tab for Trivy scan results"
  echo "  2. Check GCP billing dashboard in 24-48 hours for cost reduction"
  echo "  3. Set up lifecycle policies for image cleanup (see docs/COST_OPTIMIZATION.md)"
  exit 0
else
  echo -e "${YELLOW}⚠️  Some checks did not pass or need attention${NC}"
  echo ""
  echo "Review the output above and refer to docs/COST_OPTIMIZATION.md"
  exit 1
fi
