"""MLflow server deployment on GCP Cloud Run."""

from pathlib import Path

import pulumi
import pulumi_docker_build as docker_build
from pulumi_gcp import artifactregistry, cloudrunv2, organizations, projects


class MlflowServer(pulumi.ComponentResource):
    service: cloudrunv2.Service

    def __init__(
        self,
        service_name: str | None,
        bucket_url: pulumi.Input[str],
        mlflow_version: pulumi.Input[str],
        sa_email: pulumi.Input[str],
        backend_store_secret_id: pulumi.Input[str],
        location: pulumi.Input[str] = "us-east1",
        timeout_seconds: pulumi.Input[int] = 600,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("mlflow-selfhosting:server:MlflowServer", service_name, {}, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # necessary for proper path resolution
        DOCKER_CONTEXT_DIR = str(Path(__file__).parent.resolve())
        
        # necessary for authentication and pushing images to GCP
        client_config = organizations.get_client_config_output()

        artifact_registry_api = projects.Service(
            "artifact-registry-api",
            service="artifactregistry.googleapis.com",
            deletion_policy="ABANDON",
            disable_on_destroy=False,
            opts=child_opts,
        )

        cloud_run_api = projects.Service(
            "cloud-run-api",
            service="run.googleapis.com",
            deletion_policy="ABANDON",
            disable_on_destroy=False,
            opts=child_opts,
        )

        mlflow_repo = artifactregistry.Repository(
            "mlflow-repo",
            opts=pulumi.ResourceOptions(
                parent=self,
                depends_on=[artifact_registry_api],
            ),
            format="DOCKER",
            mode="STANDARD_REPOSITORY",
            repository_id="mlflow-repo",
            description="docker repository containing MLflow base image",
            location=location,
            docker_config={"immutable_tags": False},
            deletion_policy="DELETE",
        )


        mlflow_image = docker_build.Image(
            "mlflow-image",
            context={"location": DOCKER_CONTEXT_DIR},
            build_args={"MLFLOW_VERSION": mlflow_version},
            push=True,
            tags=[
                pulumi.Output.format(
                    "{0}/mlflow-gcp:{1}", mlflow_repo.registry_uri, mlflow_version
                )
            ],
            registries=[
                docker_build.RegistryArgs(
                    address=pulumi.Output.format("{0}-docker.pkg.dev", location),
                    username="oauth2accesstoken",
                    password=client_config.access_token,
                )
            ],
            opts=child_opts,
        )

        self.service = cloudrunv2.Service(
            service_name or "mlflow-service",
            opts=pulumi.ResourceOptions(
                parent=self,
                depends_on=[cloud_run_api],
            ),
            name=service_name or "mlflow-service",
            description="MLflow tracking server",
            location=location,
            deletion_policy="DELETE",
            deletion_protection=False,
            ingress="INGRESS_TRAFFIC_ALL",
            invoker_iam_disabled=True, # TODO: check options
            template={
                "containers": [
                    {
                        "image": mlflow_image.ref,
                        "commands": ["mlflow"],
                        "args": [
                            "server",
                            "--artifacts-destination",
                            bucket_url,
                            "--host",
                            "0.0.0.0",
                            "--disable-security-middleware",
                        ],
                        "ports": {"container_port": 5000},
                        "envs": [{
                            "name": "MLFLOW_BACKEND_STORE_URI",
                            "value_source": {
                                "secret_key_ref": {
                                    "secret": backend_store_secret_id,
                                    "version": "latest",
                                },
                            },
                        }],
                        "resources": {
                            "cpu_idle": True,
                            "limits": {
                                "cpu": "1", # TODO: check if customizable
                                "memory": "2Gi", # TODO: check if customizable
                            },
                            "startup_cpu_boost": False,
                        },
                    }
                ],
                "execution_environment": "EXECUTION_ENVIRONMENT_GEN2",
                "scaling": {
                    "max_instance_count": 1, 
                    "min_instance_count": 0,
                },
                "health_check_disabled": True, # TODO: check
                "service_account": sa_email,
                "timeout": f"{timeout_seconds}s",
            },
        )

        self.register_outputs({
            "docker_image": mlflow_image.ref,
            "url": self.service.uri,
        })