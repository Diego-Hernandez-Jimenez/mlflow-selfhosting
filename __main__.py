from components.gcp_mlflow import GcpMlflow, GcpMlflowArgs

gcp_mlflow_args = GcpMlflowArgs(
    env="dev",
    mlflow_version="v3.15.1",
    # extra_dependencies=[],
    backend_store_region="aws-us-east-1",
    backend_store_pg_version=18,
    artifact_store_region="us-east1",
    mlflow_server_region="us-east1",
)

mlflow_core = GcpMlflow("mlflow-core-full-version", gcp_mlflow_args)
