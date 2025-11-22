#!/bin/bash
# Local Trivy vulnerability testing script
# Tests .trivyignore effectiveness using existing scan reports

set -euo pipefail

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Allow skipping Docker build via environment variable
SKIP_DOCKER_BUILD="${SKIP_DOCKER_BUILD:-false}"

echo -e "${GREEN}🔍 Trivy Local Testing Utility${NC}"
echo "================================"
echo ""

# Check if Trivy is installed
if ! command -v trivy &> /dev/null; then
    echo -e "${RED}❌ Trivy is not installed${NC}"
    echo ""
    echo "Install with:"
    echo "  brew install aquasecurity/trivy/trivy"
    echo ""
    echo "Or visit: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
    exit 1
fi

echo -e "${GREEN}✅ Trivy version: $(trivy --version | head -1)${NC}"
echo ""

# Check if .trivyignore exists
if [ -f ".trivyignore" ]; then
    IGNORE_COUNT=$(grep -c "^CVE-" .trivyignore || echo "0")
    echo -e "${GREEN}✅ .trivyignore found with ${IGNORE_COUNT} CVEs configured${NC}"
else
    echo -e "${YELLOW}⚠️  No .trivyignore file found${NC}"
    IGNORE_COUNT=0
fi
echo ""

# Initialize FILTERED_COUNT early (used later in output)
FILTERED_COUNT=0

# Check if we have existing reports to analyze
if [ -d "trivy-vulnerability-reports" ]; then
    echo -e "${GREEN}📊 Analyzing existing vulnerability reports...${NC}"
    echo ""
    
    if [ -f "trivy-vulnerability-reports/trivy-report-full.txt" ]; then
        echo "Current vulnerability summary (WITHOUT .trivyignore applied):"
        grep -E "^Total:" trivy-vulnerability-reports/trivy-report-full.txt | head -1 || echo "Could not extract summary"
        echo ""
        
        # Extract and count CRITICAL and HIGH
        CRITICAL_COUNT=$(grep -c "│ CRITICAL │" trivy-vulnerability-reports/trivy-report-full.txt || echo "0")
        HIGH_COUNT=$(grep -c "│ HIGH     │" trivy-vulnerability-reports/trivy-report-full.txt || echo "0")
        
        echo "  - CRITICAL: ${CRITICAL_COUNT}"
        echo "  - HIGH: ${HIGH_COUNT}"
        echo ""
    fi
fi

# Simulate filtering with .trivyignore
if [ -f ".trivyignore" ] && [ -f "trivy-vulnerability-reports/trivy-report-full.json" ]; then
    echo -e "${GREEN}🧪 Simulating .trivyignore impact...${NC}"
    echo ""
    
    # Count how many CVEs would be filtered
    while IFS= read -r line; do
        if [[ $line =~ ^CVE-[0-9]+-[0-9]+ ]]; then
            CVE=$(echo "$line" | awk '{print $1}')
            if grep -q "$CVE" trivy-vulnerability-reports/trivy-report-full.txt 2>/dev/null; then
                ((FILTERED_COUNT++))
            fi
        fi
    done < .trivyignore
    
    echo "  📌 CVEs to be filtered by .trivyignore: ${FILTERED_COUNT}"
    echo ""
fi

# Configuration test
echo -e "${GREEN}🔧 Testing Trivy configuration...${NC}"
echo ""
trivy config Dockerfile --severity CRITICAL,HIGH,MEDIUM 2>&1 | tail -10
echo ""

# Check if Docker/Rancher is available for image scanning
if [ "$SKIP_DOCKER_BUILD" = "true" ]; then
    echo -e "${YELLOW}⏭️  Skipping Docker image build (SKIP_DOCKER_BUILD=true)${NC}"
    echo -e "${YELLOW}   Image scanning will be performed in CI/CD pipeline${NC}"
    echo ""
elif command -v docker &> /dev/null; then
    # Check if Docker daemon is responding (ignore warnings in stderr)
    if docker version --format '{{.Server.Version}}' &> /dev/null; then
        DOCKER_READY=true
    else
        DOCKER_READY=false
        
        # Try to start Rancher Desktop if available
        if [ -d "/Applications/Rancher Desktop.app" ]; then
            echo -e "${YELLOW}🚀 Starting Rancher Desktop...${NC}"
            open -a "Rancher Desktop" 2>/dev/null || true
            
            # Wait up to 90 seconds for Docker to be ready
            echo -e "${YELLOW}⏳ Waiting for Docker daemon (this may take 1-2 minutes)...${NC}"
            echo -e "${YELLOW}   Tip: Keep Rancher Desktop running to skip this wait${NC}"
            echo ""
            
            for i in {1..45}; do
                if docker version --format '{{.Server.Version}}' &> /dev/null; then
                    DOCKER_READY=true
                    echo ""
                    echo -e "${GREEN}✅ Docker daemon ready after $((i*2)) seconds${NC}"
                    break
                fi
                # Show progress every 10 seconds
                if [ $((i % 5)) -eq 0 ]; then
                    echo "   Still waiting... ($((i*2))s elapsed)"
                fi
                sleep 2
            done
            echo ""
        fi
    fi
    
    if [ "$DOCKER_READY" = true ]; then
        echo -e "${GREEN}🐳 Docker/Rancher detected and running${NC}"
        echo -e "${GREEN}🔨 Building image for vulnerability scan...${NC}"
        echo ""
        
        # Temporarily unset proxy variables that may interfere with Docker Hub access
        SAVED_HTTP_PROXY="${HTTP_PROXY:-}"
        SAVED_HTTPS_PROXY="${HTTPS_PROXY:-}"
        SAVED_http_proxy="${http_proxy:-}"
        SAVED_https_proxy="${https_proxy:-}"
        unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
        
        # Build the image (suppress most output, show only errors)
        if docker build -t gcp-todoist-runner:trivy-test . > /tmp/trivy-build.log 2>&1; then
            echo -e "${GREEN}✅ Image built successfully${NC}"
            echo ""
            echo -e "${GREEN}🔍 Scanning image for vulnerabilities...${NC}"
            echo ""
            
            # Scan with Trivy (will automatically apply .trivyignore)
            # Use --exit-code 1 to fail if vulnerabilities are found (any severity)
            TRIVY_OUTPUT=$(mktemp)
            if trivy image --severity CRITICAL,HIGH,MEDIUM,LOW,UNKNOWN --exit-code 1 gcp-todoist-runner:trivy-test 2>&1 | tee "$TRIVY_OUTPUT"; then
                echo ""
                echo -e "${GREEN}✅ No vulnerabilities found!${NC}"
                SCAN_RESULT=0
            else
                echo ""
                echo -e "${RED}❌ Vulnerabilities detected in Docker image${NC}"
                echo -e "${RED}   Blocking deployment/merge to prevent vulnerable code${NC}"
                echo ""
                
                # Show summary
                echo -e "${YELLOW}📊 Vulnerability Summary:${NC}"
                grep -E "Total:" "$TRIVY_OUTPUT" || echo "Could not extract summary"
                echo ""
                
                SCAN_RESULT=1
            fi
            rm -f "$TRIVY_OUTPUT"
            
            echo ""
            echo -e "${GREEN}💡 To see detailed report:${NC}"
            echo -e "${GREEN}   trivy image --severity CRITICAL,HIGH,MEDIUM,LOW gcp-todoist-runner:trivy-test${NC}"
            echo ""
            
            # Clean up test image to avoid accumulation
            echo -e "${GREEN}🧹 Cleaning up test image...${NC}"
            docker rmi gcp-todoist-runner:trivy-test > /dev/null 2>&1 || true
            echo -e "${GREEN}✅ Test image removed${NC}"
            echo ""
            
            # Exit with error if vulnerabilities were found
            if [ $SCAN_RESULT -ne 0 ]; then
                echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "${RED}❌ Security Check Failed${NC}"
                echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Image build failed. Check /tmp/trivy-build.log for details${NC}"
            tail -20 /tmp/trivy-build.log
            echo ""
        fi
        
        # Restore proxy variables
        [ -n "$SAVED_HTTP_PROXY" ] && export HTTP_PROXY="$SAVED_HTTP_PROXY"
        [ -n "$SAVED_HTTPS_PROXY" ] && export HTTPS_PROXY="$SAVED_HTTPS_PROXY"
        [ -n "$SAVED_http_proxy" ] && export http_proxy="$SAVED_http_proxy"
        [ -n "$SAVED_https_proxy" ] && export https_proxy="$SAVED_https_proxy"
    else
        echo -e "${YELLOW}⚠️  Docker/Rancher could not start in 90 seconds${NC}"
        echo ""
        echo -e "${YELLOW}💡 Solutions:${NC}"
        echo -e "${YELLOW}   1. Keep Rancher Desktop running in the background${NC}"
        echo -e "${YELLOW}   2. Start it manually before running code-check${NC}"
        echo -e "${YELLOW}   3. Run: bash scripts/local-trivy-test.sh (when ready)${NC}"
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  Docker/Rancher not found${NC}"
    echo -e "${YELLOW}   Install to enable image vulnerability scanning${NC}"
    echo ""
fi

# Show what would happen with .trivyignore in CI/CD
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "  1. The .trivyignore file has been created with ${IGNORE_COUNT} CVE exclusions"
echo "  2. This file will automatically be used by Trivy in CI/CD pipeline"
echo "  3. Expected result: ~${FILTERED_COUNT} fewer vulnerabilities in reports"
echo ""
echo -e "${GREEN}✅ Manual commands:${NC}"
echo "  Build: docker build -t gcp-todoist-runner:test ."
echo "  Scan:  trivy image --severity CRITICAL,HIGH gcp-todoist-runner:test"
echo ""
echo -e "${YELLOW}⚠️  Note: .trivyignore must be committed to git to work in CI/CD${NC}"
