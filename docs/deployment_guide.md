# Deployment Guide for Hierarchy Matching API on MKE

This guide describes how to deploy the Hierarchy Matching API to the MKE Kubernetes cluster.

## Prerequisites

- Access to the MKE cluster.
- `kubectl` configured with the correct context.
- Docker installed and running locally (or on the build server).
- Access to the `mtkomcr.mediatek.inc` registry.

## 1. Build the Docker Image

Navigate to the root of the repository and build the Docker image using the provided `Dockerfile`.

```bash
# Make sure you are in the project root
cd /path/to/AI-ADV

# Build the image
docker build -t mtkomcr.mediatek.inc/srv-mke-aas1/hierarchy-matching-api:latest .
```

## 2. Push the Image to the Registry

Log in to the registry (if not already logged in) and push the image.

```bash
docker login mtkomcr.mediatek.inc
docker push mtkomcr.mediatek.inc/srv-mke-aas1/hierarchy-matching-api:latest
```

## 3. Deploy to MKE

The deployment configuration is defined in `mke-project-deploy.yaml`. This file defines both the Deployment (pods) and the Service (network access).

### Verify Configuration

Ensure `mke-project-deploy.yaml` has the correct image tag and namespace.

```yaml
image: mtkomcr.mediatek.inc/srv-mke-aas1/hierarchy-matching-api:latest
```

### Apply Configuration

Use `kubectl` to apply the configuration.

```bash
kubectl apply -f mke-project-deploy.yaml
```

## 4. Verify Deployment

Check the status of the deployment and pods.

```bash
# Check deployment status
kubectl get deployment -n srv-mke-aas1

# Check pods
kubectl get pods -n srv-mke-aas1
```

Wait until the pod status is `Running` and `READY` is `1/1`.

## 5. Access the API

The service is exposed via a NodePort (or ClusterIP depending on configuration).

To check the service details:

```bash
kubectl get svc -n srv-mke-aas1
```

If using NodePort, you can access the API at `http://<node-ip>:<node-port>`.

### Getting the Connection Details

1.  **Find the NodePort:**
    Run the following command to see the assigned port (look under `PORT(S)` column, e.g., `8000:31234/TCP`):
    ```bash
    kubectl get svc mke-aas1-service -n srv-mke-aas1
    ```
    The second port number (e.g., `31234`) is your NodePort.

2.  **Find a Node IP:**
    Get the IP address of any node in the cluster:
    ```bash
    kubectl get nodes -o wide
    ```
    Use the `INTERNAL-IP` (or `EXTERNAL-IP` if available/reachable) of any node.

3.  **Construct URL:**
    `http://<NODE-IP>:<NODE-PORT>`

### Test the Endpoint

You can verify the service is running by accessing the health check endpoint:

```bash
curl http://<service-ip>:<port>/health
```

Or the API documentation:

```bash
http://<service-ip>:<port>/docs
```

