"""The database in which entity metadata (e.g. trace info, experiment tracking metadata) is stored"""

import os
from enum import IntEnum
from typing import TypedDict

import pulumi
import pulumi_neon as neon
from pulumi_gcp import projects, secretmanager


class PgVersion(IntEnum):
    PG14 = 14
    PG15 = 15
    PG16 = 16
    PG17 = 17
    PG18 = 18


class BackendStoreArgs(TypedDict):
    project_name: str
    branch_name: str
    pg_version: PgVersion
    region_id: str


class BackendStore(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        args: BackendStoreArgs,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("mlflow-selfhosting:backend:BackendStore", name, {}, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # assumes hobby plan (less customizable)
        self.project = neon.Project(
            name,
            branch={
                "database_name": "mlflow-backend-store",
                "name": args.get("branch_name"),
            },
            default_branch_protected=False,
            history_retention_seconds=21600,
            name=args.get("project_name"),
            org_id=os.environ["NEON_ORGANIZATION_ID"],
            pg_version=args.get("pg_version"),
            region_id=args.get("region_id"),
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

        edited_conn_uri = self.project.connection_uri_pooler.apply(
            lambda uri: uri.replace(
                "postgres", "postgresql", 1
            )  # necessary to work with mlflow
        )
        self.backend_store_uri = edited_conn_uri

        secretmanager.SecretVersion(
            "backend-store-uri",
            secret=self.backend_store_uri_secret.secret_id,
            secret_data=edited_conn_uri,
            opts=child_opts,
        )

        self.register_outputs(
            {
                "neon_project": self.project.id,
                "backend_store_name": self.project.database_name,
                "backend_store_uri_secret_id": self.backend_store_uri_secret.id,
            }
        )
