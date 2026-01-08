#!/bin/tcsh

# Configuration
set IMAGE_NAME = "mtkomcr.mediatek.inc/srv-mke-aas1/hierarchy-matching-api"
set TAG = "latest"
set FULL_IMAGE = "${IMAGE_NAME}:${TAG}"
set NAMESPACE = "srv-mke-aas1"
set DEPLOY_FILE = "mke-project-deploy.yaml"
set SERVICE_NAME = "mke-aas1-service"

# Flags
set SKIP_BUILD = "false"
set SKIP_PUSH = "false"

# Parse arguments
while ( $#argv > 0 )
    switch ( $1 )
        case "--no-build":
            set SKIP_BUILD = "true"
            breaksw
        case "--no-push":
            set SKIP_PUSH = "true"
            breaksw
        default:
            echo "Unknown parameter passed: $1"
            exit 1
            breaksw
    endsw
    shift
end

echo "=================================================="
echo "Deployment Script for Hierarchy Matching API"
echo "Target Image: $FULL_IMAGE"
echo "Namespace: $NAMESPACE"
echo "=================================================="

# Check if running from root
if ( ! -f "$DEPLOY_FILE" ) then
    echo "Error: $DEPLOY_FILE not found. Please run this script from the project root."
    exit 1
endif

# Step 1: Build Image
if ( "$SKIP_BUILD" == "false" ) then
    echo ""
    echo "[1/4] Building Docker image..."
    docker build -t "$FULL_IMAGE" .
    if ( $status != 0 ) exit 1
else
    echo ""
    echo "[1/4] Skipping build..."
endif

# Step 2: Push Image
if ( "$SKIP_PUSH" == "false" ) then
    echo ""
    echo "[2/4] Pushing image to registry..."
    echo "Note: Ensure you are logged in (docker login mtkomcr.mediatek.inc)"
    docker push "$FULL_IMAGE"
    if ( $status != 0 ) exit 1
else
    echo ""
    echo "[2/4] Skipping push..."
endif

# Step 3: Deploy to Kubernetes
echo ""
echo "[3/4] Applying Kubernetes configuration..."
kubectl apply -f "$DEPLOY_FILE"
if ( $status != 0 ) exit 1

echo "Waiting for deployment rollout..."
kubectl rollout status deployment/mke-aas1-deploy -n "$NAMESPACE"
if ( $status != 0 ) exit 1

# Step 4: Display Connection Info
echo ""
echo "[4/4] Deployment Info:"

# Get NodePort
set NODE_PORT = `kubectl get svc "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}'`
if ( $status != 0 ) then
    echo "Failed to get NodePort"
    exit 1
endif

# Get a Node IP (using the first one found)
set NODE_IP = `kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'`

if ( "$NODE_IP" == "" ) then
    # Fallback if InternalIP is not found or jsonpath fails
    set NODE_IP = `kubectl get nodes -o wide | awk 'NR==2 {print $6}'`
endif

echo "--------------------------------------------------"
echo "Service is exposed via NodePort."
echo "URL: http://${NODE_IP}:${NODE_PORT}"
echo "Health Check: http://${NODE_IP}:${NODE_PORT}/health"
echo "Docs: http://${NODE_IP}:${NODE_PORT}/docs"
echo "--------------------------------------------------"
