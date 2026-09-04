# Pulumi GCP & Neon MLflow deployment plugin

This Pulumi Python plugin automates the deployment of a fully functional MLflow environment using Google Cloud Platform (GCP) and Neon. It provisions a Google Cloud Storage bucket for the artifact store, a Neon serverless Postgres database for the backend store, and a Cloud Run tracking server with the MLflow UI. It's based on the official [Mlflow guide for deploying on GCP](https://mlflow.org/docs/latest/self-hosting/deploy-to-cloud/gcp/) with some notable differences (see the **Why Neon?** section).

## Prerequisites

- **Python Environment**: Python 3.12 or newer is required.
- **Cloud Accounts**: You need a Google Cloud account with a target GCP project, as well as a Neon account.
- **Pulumi**: Ensure the Pulumi CLI is installed and authenticated to your account.
- **Dependencies**: Your Pulumi project must have access to `pulumi` and `pulumi-gcp`. See [here](https://www.pulumi.com/docs/iac/get-started/gcp/) for instructions on how to initialize a Pulumi project with GCP.

## Authentication and API keys

You must authenticate with both cloud providers before initializing the deployment.

1. **Google Cloud**: Authenticate your environment via `gcloud auth login` or by exporting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.
2. **Neon**: You must export your authentication keys as environment variables. Create a file named `env.sh` (you can copy `env.sh.template`) and fill in your credentials:

   ```bash
   export NEON_API_KEY="<YOUR_NEON_API_KEY>"
   export NEON_ORGANIZATION_ID="<YOUR_NEON_ORGANIZATION_ID>"
   ```
   Then run `source env.sh` in your terminal so Pulumi can access these required variables.

## Installation

You can import this plugin directly from its Git repository. The plugin source lives in the `plugin/` subdirectory. Add the following to your environment:

```bash
# pulumi package add <repo_url>/plugin@<release-version>
pulumi package add https://github.com/Diego-Hernandez-Jimenez/mlflow-selfhosting/plugin
```

> **Note:** The import `from diego_hernandez_jimenez_mlflow_selfhosting import ...` shown below is only available after running `pulumi package add`, which generates a local SDK. You cannot install it directly with `pip`.

## Usage

The plugin exposes a unified `GcpMlflow` component that automatically wires together the backend store, artifact store, IAM permissions, and the Cloud Run server.

Add the following to your `__main__.py` file to deploy the full infrastructure:

```python

# ugly package name, I know, I'll try to edit it
from diego_hernandez_jimenez_mlflow_selfhosting import GcpMlflowArgs, GcpMlflow

gcp_mlflow_args = GcpMlflowArgs(
    env="dev",
    mlflow_version="v3.15.1",
    # extra_dependencies=[], # already includes google-cloud-storage
    backend_store_region="aws-us-east-1",
    backend_store_pg_version=18,
    artifact_store_region="us-east1",
    mlflow_server_region="us-east1",
)

mlflow_core = GcpMlflow("mlflow-core-full-version", gcp_mlflow_args)
```

Run `pulumi up` to preview and provision the resources. Upon completion, the console will output the active tracking URI for your MLflow instance and the storage URI for your artifacts.

## Connecting to your tracking server

Once deployed, you can point your local Python training scripts to the new remote tracking server:

```python
import mlflow

# Set the tracking URI to the Cloud Run URL output by Pulumi
mlflow.set_tracking_uri("<YOUR_CLOUDRUN_TRACKING_URL>")

# ...
```

Visit your cloud run url endpoint normally to see all the generated metadata.

## Why Neon?

While it is true that the official docs use Cloud SQL as the backend store, the reality is that we don't need an active SQL instance running 24/7, only when using MLflow and logging metadata. Also, this plugin is aimed at solo developers who want to use the cloud without spending anything (the deployed resources here fit perfectly in the GCP free tier and Neon free plan).

## Things to consider

- **Opinionated plugin**: I've fixed many arguments and configuration variables. I believe they are sensible choices, but I may change the API later to make it more flexible.

- **Public endpoints**: The Cloud Run endpoint and the Neon database are public. Be mindful of this. Unfortunately, with the free plans, you cannot restrict them to private networks.

- **Cold starts**: Both the Cloud Run service and Neon will experience cold starts. Because these resources are serverless, they scale to 0 after some idle time without activity.

- **Large Model Upload Timeouts**: When training locally, uploading large models (like Scikit-Learn's Random Forest) to Google Cloud Storage might fail or time out. This is a bottleneck caused by your local upload bandwidth struggling with massive files. To resolve this:

    - Optimize the Algorithms: Some Scikit-Learn trees save their structure inefficiently, easily resulting in 500 MB+ files. Sometimes switching to other libraries like XGBoost or LightGBM (when training boosting models) achieves similar or better performance while keeping model sizes under a few megabytes. This avoids the timeout problem completely.

    - Train in the Cloud: Arguably the best solution for production-like settings or heavy models. Move training to a VM (Compute Engine) or Vertex AI. Uploading to GCS from within Google's internal network is instantaneous compared to your local ISP.
