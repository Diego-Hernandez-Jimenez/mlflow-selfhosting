from components.gcp_mlflow import GcpMlflow
from pulumi.provider.experimental import component_provider_host

if __name__ == "__main__":
    component_provider_host([GcpMlflow], "mlflow_selfhosting", version="0.1.0")
