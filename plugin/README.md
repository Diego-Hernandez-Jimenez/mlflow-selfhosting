# Architecture Components (`mlflow-selfhosting`)

This project is built with a **modular design** using reusable Pulumi components. This structure breaks down the self-hosted MLflow architecture on Google Cloud Platform into independent, self-contained modules (backend metadata, artifact storage, identity/security, and server compute).

> **Note:** Although each component is defined independently to allow individual imports, **currently only the main orchestrator component `GcpMlflow` is exposed for public import**.

---

## Architecture Overview & MLflow Connection

Following [MLflow's Self-Hosting Architecture Guidelines](https://mlflow.org/docs/latest/self-hosting/), a remote MLflow Tracking Server requires four distinct layers:
1. **Backend Store** for structured metadata (Relational database, like PostgreSQL).
2. **Artifact Store** for heavy binary files (Google Cloud Storage).
3. **Tracking Server** running the `mlflow server` process and web UI (Cloud Run).
4. **IAM / Identity** for secure, role-based cloud permissions.

---

## Component Breakdown

### 1. `GcpMlflow`

The top-level orchestrator for the entire self-hosted MLflow core infrastructure on GCP + Neon. Integrates `BackendStore`, `ArtifactStore`, `MlflowIam`, and `TrackingServer` into a unified deployment. It outputs the public `tracking_uri` (Cloud Run URL) and `artifact_store_uri` (`gs://` bucket link).

This is the primary component users instantiate to spin up a fully configured remote MLflow environment. MLflow Python SDK clients connect to it via `mlflow.set_tracking_uri(tracking_uri)`.

* **Publicly Exposed:** **Yes** (currently the main exported component).

---

### 2. `BackendStore`

Provisions a managed PostgreSQL database hosted on **Neon** and securely stores its connection URI in GCP Secret Manager. Serves as the **MLflow Backend Store** passed to the server via the `MLFLOW_BACKEND_STORE_URI` environment variable and it's used to persist non-file metadata across experiments:

  * Run parameters, metrics, tags, and timestamps.
  * MLflow Tracing and evaluation metadata.
  * Experiment structure and Model Registry state.
  * Enabling concurrent multi-user tracking and querying.

---

### 3. `ArtifactStore`

Provisions a Google Cloud Storage (GCS) bucket configured with enterprise security defaults (enforced public access prevention, uniform bucket-level access, and autoclass storage management). Serves as the **MLflow Default Artifact Root** passed to the server and stores artifacts generated during the machine learning lifecycle:

  * Logged model weights and binaries (e.g., PyTorch, TensorFlow, Scikit-learn, ONNX models).
  * Datasets, plots, figures, prompt templates, and evaluation artifacts.

---

### 4. `TrackingServer`

Builds a custom MLflow Docker image (pushed to GCP Artifact Registry) and deploys the `mlflow server` process onto a serverless Google Cloud Run service. Acts as the central **MLflow Tracking Server & Web UI**:

  * **API & UI Host:** Serves the REST API endpoints used by the MLflow SDK (`mlflow.log_params`, `mlflow.log_artifact`, etc.) and renders the web interface for experiment visualization.
  * **Direct Artifact Uploads:** Uses `--default-artifact-root` so clients transfer large model files directly to GCS, avoiding Cloud Run request payload limits and memory timeouts.
  * **Secret Integration:** Safely injects the PostgreSQL database credentials directly from GCP Secret Manager at startup without exposing plaintext passwords in environment definitions.

---

### 5. `MlflowIam`

Manages identity and access control (IAM) resources within GCP, adhering to the principle of least privilege. Binds a dedicated GCP Service Account (`mlflow-sa`) to the Cloud Run Tracking Server to ensure interactions between MLflow, GCS, and Secret Manager are authenticated natively via IAM:

  * **GCS Access:** Grants `roles/storage.objectUser` on the `ArtifactStore` bucket, allowing the tracking server to read, write, and manage logged artifacts.
  * **Secret Access:** Grants `roles/secretmanager.secretAccessor` so the server process can dynamically fetch the `BackendStore` database URI from Secret Manager.
