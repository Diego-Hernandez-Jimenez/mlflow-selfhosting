from dataclasses import dataclass

import pulumi
from src import artifact_store, iam
from src.backend_store import BackendStore
from src.mlflow_service import tracking_server


@dataclass
class GcpMlflowArgs:
    env: pulumi.Input[str] = "dev"
    mlflow_version: pulumi.Input[str] = "v3.15.1"
    backend_store_region: pulumi.Input[str] = "aws-us-east-1"
    backend_store_pg_version: pulumi.Input[str] = 18
    artifact_store_region: pulumi.Input[str] = "us-east1"
    mlflow_server_region: pulumi.Input[str] = "us-east1"


class GcpMlflow(pulumi.ComponentResource):
    tracking_uri: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: GcpMlflowArgs | None = None,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("mlflow-selfhosting:index:GcpMlflow", name, {}, opts)

        # pulumi hierarchy
        child_opts = pulumi.ResourceOptions(parent=self)

        # Backend Store
        self.backend = BackendStore(
            "mlflow-backend-store",
            branch_name=args.env,
            pg_version=args.backend_store_pg_version,
            region_id=args.backend_store_region,
            config=args.backend_store_config,
            opts=child_opts,
        )

        # Artifact Store
        self.artifact_store = artifact_store.ArtifactStore(
            "mlflow-artifact-store",
            region=args.artifact_store_region,
            opts=child_opts,
        )

        # IAM
        self.iam = iam.IamRoles(
            "mlflow-iam",
            bucket_name=self.artifact_store.bucket.name,
            neon_db_secret=self.backend.db_secret,
            opts=child_opts,
        )

        # MLflow Server
        self.server = tracking_server.Server(
            "mlflow-service",
            bucket_url=self.artifact_store.bucket_url,
            mlflow_version=args.mlflow_version,
            sa_email=self.iam.service_account.email,
            backend_store_secret_uri=self.backend.db_secret.id,
            region=args.mlflow_server_region,
            opts=child_opts,
        )

        self.tracking_uri = self.server.url

        self.register_outputs({
            "tracking_uri": self.tracking_uri,
            "artifact_store_uri": self.artifact_store
        })