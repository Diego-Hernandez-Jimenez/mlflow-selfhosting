"""A Google Cloud + Neon Python Pulumi plugin"""

# Explicit component registration
from pulumi.provider.experimental import component_provider_host

from components.artifact_store import ArtifactStore  # noqa: F401
from components.backend_store import BackendStore  # noqa: F401
from components.gcp_mlflow import GcpMlflow  # noqa: F401
from components.iam import MlflowIam  # noqa: F401
from components.mlflow_service.tracking_server import MlflowServer  # noqa: F401

if __name__ == "__main__":
    component_provider_host(
        [ArtifactStore, BackendStore, GcpMlflow, MlflowIam, MlflowServer],
        "mlflow-selfhosting",
        version="1.0.0",
    )
