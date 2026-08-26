"""IAM roles and service accounts for MLflow access."""

import pulumi
from pulumi_gcp import secretmanager, serviceaccount
from pulumi_gcp import storage as gcs


class MlflowIam(pulumi.ComponentResource):
    service_account: serviceaccount.Account

    def __init__(
        self,
        service_account_name: str,
        bucket_name: pulumi.Input[str],
        neon_db_secret_id: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("mlflow-selfhosting:iam:MlflowIam", service_account_name, {}, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        self.service_account = serviceaccount.Account(
            service_account_name or "mlflow-sa",
            account_id="mlflow-sa",
            create_ignore_already_exists=True,
            deletion_policy="DELETE",
            description="MLflow service account",
            disabled=False,
            display_name=service_account_name or "mlflow-sa",
            opts=child_opts,
        )

        gcs.BucketIAMBinding(
            "mlflow-bucket-permissions",
            bucket=bucket_name,
            members=[self.service_account.member],
            role="roles/storage.objectUser",
            opts=child_opts,
        )

        secretmanager.SecretIamMember(
            "backend-store-uri-secret-access",
            secret_id=neon_db_secret_id,
            role="roles/secretmanager.secretAccessor",
            member=pulumi.Output.format("serviceAccount:{0}", self.service_account.email),
            opts=child_opts,
        )

        self.register_outputs({
            "service_account_email": self.service_account.email,
        })