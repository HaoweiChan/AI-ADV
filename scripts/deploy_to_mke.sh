#!/bin/bash

# Exit on any error
set -e

# Configuration
IMAGE_NAME="mtkomcr.mediatek.inc/srv-mke-aas1/hierarchy-matching-api"
TAG="latest"
FULL_IMAGE="${IMAGE_NAME}:${TAG}"
NAMESPACE="srv-mke-aas1"
DEPLOY_FILE="mke-project-deploy.yaml"
SERVICE_NAME="mke-aas1-service"

# Flags
SKIP_BUILD=false
SKIP_PUSH=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --no-build) SKIP_BUILD=true ;;
        --no-push) SKIP_PUSH=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "=================================================="
echo "Deployment Script for Hierarchy Matching API"
echo "Target Image: $FULL_IMAGE"
echo "Namespace: $NAMESPACE"
echo "=================================================="

# Check if running from root
if [ ! -f "$DEPLOY_FILE" ]; then
    echo "Error: $DEPLOY_FILE not found. Please run this script from the project root."
    exit 1
fi

# Step 1: Build Image
if [ "$SKIP_BUILD" = false ]; then
    echo ""
    echo "[1/4] Building Docker image..."
    docker build -t "$FULL_IMAGE" .
else
    echo ""
    echo "[1/4] Skipping build..."
fi

# Step 2: Push Image
if [ "$SKIP_PUSH" = false ]; then
    echo ""
    echo "[2/4] Pushing image to registry..."
    echo "Note: Ensure you are logged in (docker login mtkomcr.mediatek.inc)"
    docker push "$FULL_IMAGE"
else
    echo ""
    echo "[2/4] Skipping push..."
fi

# Step 3: Deploy to Kubernetes
echo ""
echo "[3/4] Applying Kubernetes configuration..."
kubectl apply -f "$DEPLOY_FILE"

echo "Waiting for deployment rollout..."
kubectl rollout status deployment/mke-aas1-deploy -n "$NAMESPACE"

# Step 4: Display Connection Info
echo ""
echo "[4/4] Deployment Info:"

# Get NodePort
NODE_PORT=$(kubectl get svc "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}')
# Get a Node IP (using the first one found)
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

if [ -z "$NODE_IP" ]; then
    # Fallback if InternalIP is not found or jsonpath fails
    NODE_IP=$(kubectl get nodes -o wide | awk 'NR==2 {print $6}')
fi

echo "--------------------------------------------------"
echo "Service is exposed via NodePort."
echo "URL: http://${NODE_IP}:${NODE_PORT}"
echo "Health Check: http://${NODE_IP}:${NODE_PORT}/health"
echo "Docs: http://${NODE_IP}:${NODE_PORT}/docs"
echo "--------------------------------------------------"

