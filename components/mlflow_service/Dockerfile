# ref: https://mlflow.org/docs/latest/self-hosting/deploy-to-cloud/gcp/
# Based on the official MLflow docker image, but preinstalls "google-cloud-storage" package which is required by MLflow server to access Google Cloud storage

ARG MLFLOW_VERSION

FROM ghcr.io/mlflow/mlflow:${MLFLOW_VERSION}-full

COPY requirements.txt .
RUN pip install -r requirements.txt