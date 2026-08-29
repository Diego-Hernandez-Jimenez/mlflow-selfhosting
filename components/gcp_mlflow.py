"""Full Mlflow core resource stack for GCP + Neon"""

from typing import TypedDict

import pulumi

from .artifact_store import ArtifactStore, ArtifactStoreArgs
from .backend_store import BackendStore, BackendStoreArgs, PgVersion
from .iam import IamArgs, MlflowIam
from .tracking_server import TrackingServer, TrackingServerArgs


class GcpMlflowArgs(TypedDict):
    env: str
    mlflow_version: str
    extra_dependencies: list[str] | None
    backend_store_region: str
    backend_store_pg_version: int
    artifact_store_region: str
    mlflow_server_region: str


class GcpMlflow(pulumi.ComponentResource):
    tracking_uri: pulumi.Output[str]
    artiact_store_uri: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: GcpMlflowArgs,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("mlflow-selfhosting:index:GcpMlflow", name, {}, opts)
            
        # pulumi hierarchy
        child_opts = pulumi.ResourceOptions(parent=self)

        # Backend Store
        self.backend = BackendStore(
            "mlflow-backend-store",
            args=BackendStoreArgs(
               project_name="mlflow-backend-store",
               branch_name=args.get("env"),
               pg_version=PgVersion(args.get("backend_store_pg_version")),
               region_id=args.get("backend_store_region")
           ),
            opts=child_opts,
        )

        # Artifact Store
        self.artifact_store = ArtifactStore(
            "mlflow-artifact-store",
            args=ArtifactStoreArgs(location=args.get("artifact_store_region")),
            opts=child_opts,
        )

        # IAM
        self.iam = MlflowIam(
            "mlflow-iam",
            args=IamArgs(
                bucket_name=self.artifact_store.bucket.name,
                backend_store_uri_secret_id=self.backend.backend_store_uri_secret.secret_id,
            ),
            opts=child_opts,
        )

        # MLflow Server
        self.tracking_server = TrackingServer(
            "mlflow-service",
            args=TrackingServerArgs(
                bucket_url=self.artifact_store.bucket.url,
                mlflow_version=args.get("mlflow_version"),
                extra_dependencies=args.get("extra_dependencies") or [],
                sa_email=self.iam.service_account.email,
                backend_store_secret_id=self.backend.backend_store_uri_secret.secret_id,
                backend_store_uri=self.backend.backend_store_uri,
                region=args.get("mlflow_server_region"),
                timeout_seconds=600,
            ),
            opts=child_opts,
        )

        self.tracking_uri = self.tracking_server.service.uri

        self.register_outputs(
            {
                "tracking_uri": self.tracking_uri,
                "artifact_store_uri": self.artifact_store,
            }
        )
