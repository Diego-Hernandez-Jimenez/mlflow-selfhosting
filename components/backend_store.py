import os
from typing import Literal

import pulumi
import pulumi_neon as neon
from pulumi_gcp import projects, secretmanager


class BackendStore(pulumi.ComponentResource):
    def __init__(
        self,
        name: str | None,
        branch_name: str,
        pg_version: Literal[14, 15, 16, 17, 18],
        region_id: str,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("mlflow-selfhosting:backend:BackendStore", name, {}, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # assumes hobby plan (less customizable)
        self.project = neon.Project(
            name or "neon-project",
            branch={
                "database_name": name or "mlflow_backend_store",
                "name": branch_name,
            },
            default_branch_protected=False,
            history_retention_seconds=21600,
            name=name or "neon-project",
            org_id=os.environ["NEON_ORGANIZATION_ID"],
            pg_version=pg_version,
            region_id=region_id,
            opts=child_opts,
        )

        secret_api = projects.Service(
            "secret-api",
            service="secretmanager.googleapis.com",
            deletion_policy="ABANDON",
            disable_on_destroy=False,
            opts=child_opts,
        )

        self.backend_store_uri_secret = secretmanager.Secret(
            "backend-store-uri-secret",
            secret_id="backend-store-uri-secret",
            replication={"auto": {}},
            deletion_protection=False,
            deletion_policy="DELETE",
            opts=pulumi.ResourceOptions(
                parent=self,
                depends_on=[secret_api],
            ),
        )

        secretmanager.SecretVersion(
            "backend-store-uri",
            secret=self.backend_store_uri_secret.secret_id,
            secret_data=self.project.connection_uri.apply(
                lambda uri: uri.replace("postgres", "postgresql", 1) # necessary to work with mlflow
            ),
            opts=child_opts,
        )

        self.register_outputs({
            "neon_project": self.project.id,
            "backend_store_name": self.project.database_name,
            "backend_store_uri_secret_id": self.backend_store_uri_secret.id,
        })