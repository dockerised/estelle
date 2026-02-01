#!/bin/bash
# =============================================================================
# Estelle Manor Padel Booking - Build and Push to Control Plane Registry
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAG="${TAG:-latest}"
ORG="${CPLN_ORG:-george-crosby-015c08}"
SERVICE="gc-estelle-padel-booking"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build and push Estelle Manor Padel Booking Docker image to Control Plane registry.

Options:
    -o, --org ORG       Control Plane organization name (default: george-crosby-015c08)
    -t, --tag TAG       Image tag (default: latest)
    -b, --build-only    Build image without pushing
    -h, --help          Show this help message

Examples:
    # Build and push with default settings
    $0

    # Build and push with specific tag
    $0 --tag v1.0.0

    # Build only (no push)
    $0 --build-only

Environment Variables:
    CPLN_ORG    Control Plane organization name
    TAG         Image tag (default: latest)
EOF
    exit 0
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if cpln CLI is installed
    if ! command -v cpln &> /dev/null; then
        log_error "cpln CLI is not installed. Please install it first:"
        echo "  curl -s https://raw.githubusercontent.com/controlplane-com/cli/main/install.sh | sh"
        exit 1
    fi

    # Check if logged in to cpln
    if ! cpln profile current &> /dev/null; then
        log_error "Not logged in to Control Plane. Please run: cpln login"
        exit 1
    fi

    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

build_image() {
    local image_name="$SERVICE:$TAG"

    log_info "Building image: $image_name"

    docker build \
        -t "$image_name" \
        -f "$SCRIPT_DIR/Dockerfile" \
        "$SCRIPT_DIR"

    log_success "Built: $image_name"
}

push_image() {
    local local_image="$SERVICE:$TAG"

    log_info "Pushing image to Control Plane: $local_image"

    # Use cpln image docker-login to authenticate
    cpln image docker-login

    # Tag for Control Plane registry
    local cpln_registry="$ORG.registry.cpln.io"
    local cpln_image="$cpln_registry/$SERVICE:$TAG"

    docker tag "$local_image" "$cpln_image"
    docker push "$cpln_image"

    log_success "Pushed: $cpln_image"
    log_success "Available as: /org/$ORG/image/$SERVICE:$TAG"
}

# =============================================================================
# Main Script
# =============================================================================

# Parse arguments
BUILD_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--org)
            ORG="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -b|--build-only)
            BUILD_ONLY=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Header
echo ""
echo "=============================================="
echo "  Estelle Manor Padel Booking"
echo "  Build & Push to Control Plane"
echo "=============================================="
echo ""

# Check prerequisites
check_prerequisites

log_info "Organization: $ORG"
log_info "Service: $SERVICE"
log_info "Tag: $TAG"
echo ""

# Build image
if ! build_image; then
    log_error "Build failed"
    exit 1
fi

# Push image (unless build-only)
if [[ "$BUILD_ONLY" == "false" ]]; then
    if ! push_image; then
        log_error "Push failed"
        exit 1
    fi
fi

# Summary
echo ""
echo "=============================================="
echo "  Summary"
echo "=============================================="
log_success "Image ready: /org/$ORG/image/$SERVICE:$TAG"
echo ""
echo "Next steps:"
echo "  1. Set credentials (if not already set):"
echo "     export TF_VAR_estelle_username='your.email@example.com'"
echo "     export TF_VAR_estelle_password='your_password'"
echo "     export TF_VAR_discord_webhook_url='https://discord.com/api/webhooks/...'"
echo "  2. Deploy with Terraform:"
echo "     cd terraform && terraform init && terraform apply"
echo ""
