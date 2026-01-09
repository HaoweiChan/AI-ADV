#!/bin/tcsh

# Configuration
set IMAGE_NAME = "mtkomcr.mediatek.inc/srv-mke-aas1/hierarchy-matching-api"
set TAG = "latest"
set FULL_IMAGE = "${IMAGE_NAME}:${TAG}"
set NAMESPACE = "srv-mke-aas1"
set DEPLOY_FILE = "mke-project-deploy.yaml"
set SERVICE_NAME = "mke-aas1-service"

# Harbor Configuration
set HARBOR_SERVER = "mtkomcr.mediatek.inc"
set SECRET_NAME = "mke-aas1-harbor-secret"
# UPDATE THESE CREDENTIALS
set HARBOR_USER = "robot\$srv-mke-aas1+robot"
set HARBOR_PASSWORD = "YOUR_HARBOR_PASSWORD"
set HARBOR_EMAIL = "mtkxxxx@mediatek.com"

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

# Step 1: Ensure Image Pull Secret Exists
echo ""
echo "[1/3] Checking Image Pull Secret..."

# Check if secret exists
kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" >& /dev/null

if ( $status != 0 ) then
    echo "Secret '$SECRET_NAME' not found. Creating..."
    
    if ( "$HARBOR_PASSWORD" == "YOUR_HARBOR_PASSWORD" ) then
        echo "Error: Please update HARBOR_PASSWORD in the script before running."
        exit 1
    endif

    kubectl create secret docker-registry "$SECRET_NAME" \
        -n "$NAMESPACE" \
        --docker-server="$HARBOR_SERVER" \
        --docker-username="$HARBOR_USER" \
        --docker-password="$HARBOR_PASSWORD" \
        --docker-email="$HARBOR_EMAIL"
    
    if ( $status != 0 ) then
        echo "Failed to create secret."
        exit 1
    endif
    echo "Secret created successfully."
else
    echo "Secret '$SECRET_NAME' already exists. Skipping creation."
endif

# Step 2: Deploy to Kubernetes
echo ""
echo "[2/3] Applying Kubernetes configuration..."
kubectl apply -f "$DEPLOY_FILE"
if ( $status != 0 ) exit 1

echo "Waiting for deployment rollout..."
kubectl rollout status deployment/mke-aas1-deploy -n "$NAMESPACE"
if ( $status != 0 ) exit 1

# Step 3: Display Connection Info
echo ""
echo "[3/3] Deployment Info:"

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
