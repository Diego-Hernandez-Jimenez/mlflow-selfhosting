"""IAM roles and service accounts for MLflow access."""

from typing import TypedDict

import pulumi
from pulumi_gcp import secretmanager, serviceaccount
from pulumi_gcp import storage as gcs


class IamArgs(TypedDict):
    bucket_name: pulumi.Input[str]
    backend_store_uri_secret_id: pulumi.Input[str]


class MlflowIam(pulumi.ComponentResource):
    service_account: serviceaccount.Account

    def __init__(
        self,
        name: str,
        args: IamArgs,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("mlflow-selfhosting:iam:MlflowIam", name, {}, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        self.service_account = serviceaccount.Account(
            name,
            account_id="mlflow-sa",
            create_ignore_already_exists=True,
            deletion_policy="DELETE",
            description="MLflow service account",
            disabled=False,
            display_name="mlflow-sa",
            opts=child_opts,
        )

        gcs.BucketIAMBinding(
            "mlflow-bucket-permissions",
            bucket=args.get("bucket_name"),
            members=[self.service_account.member],
            role="roles/storage.objectUser",
            opts=child_opts,
        )

        secretmanager.SecretIamMember(
            "backend-store-uri-secret-access",
            secret_id=args.get("backend_store_uri_secret_id"),
            role="roles/secretmanager.secretAccessor",
            member=pulumi.Output.format(
                "serviceAccount:{0}", self.service_account.email
            ),
            opts=child_opts,
        )

        self.register_outputs(
            {
                "service_account_email": self.service_account.email,
            }
        )
