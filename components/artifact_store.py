"""Artifact store: Blob storage for larger pieces of persisted data."""

import pulumi
from pulumi_gcp import storage as gcs


class ArtifactStore(pulumi.ComponentResource):
    bucket: gcs.Bucket

    def __init__(
        self,
        name: str | None,
        location: pulumi.Input[str] = "us-east1",
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("mlflow-selfhosting:artifact:ArtifactStore", name, {}, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        self.bucket = gcs.Bucket(
            name or "mlflow-artifact-store",
            location=location,
            force_destroy=True, # careful
            default_event_based_hold=False,
            deletion_policy="DELETE",
            enable_object_retention=False,
            autoclass={
                "enabled": True,
                "terminal_storage_class": "NEARLINE",
            },
            requester_pays=False,
            public_access_prevention="enforced",
            storage_class="STANDARD",
            uniform_bucket_level_access=True,
            opts=child_opts,
        )

        self.register_outputs({
            "bucket_name": self.bucket.name,
            "bucket_url": self.bucket.url,
        })