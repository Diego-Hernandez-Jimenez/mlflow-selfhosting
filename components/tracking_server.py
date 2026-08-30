"""MLflow server deployment on GCP Cloud Run."""

from typing import TypedDict

import pulumi
import pulumi_docker_build as docker_build
from pulumi_gcp import artifactregistry, cloudrunv2, organizations, projects


class TrackingServerArgs(TypedDict):
    bucket_url: pulumi.Input[str]
    mlflow_version: pulumi.Input[str]
    extra_dependencies: list[pulumi.Input[str]]
    sa_email: pulumi.Input[str]
    backend_store_secret_id: pulumi.Input[str]
    region: pulumi.Input[str]
    timeout_seconds: pulumi.Input[int]


class TrackingServer(pulumi.ComponentResource):
    service: cloudrunv2.Service

    def __init__(
        self,
        name: str | None,
        args: TrackingServerArgs,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("mlflow-selfhosting:server:MlflowServer", name, {}, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # necessary for proper path resolution
        # DOCKER_CONTEXT_DIR = str(Path(__file__).parent.resolve())
        dockerfile = f"""
        FROM ghcr.io/mlflow/mlflow:{args.get("mlflow_version")}-full
        RUN pip install google-cloud-storage {" ".join(args.get("extra_dependencies"))}
        """

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
            location=args.get("region"),
            docker_config={"immutable_tags": False},
            deletion_policy="DELETE",
        )

        mlflow_image = docker_build.Image(
            "mlflow-image",
            # context={"location": DOCKER_CONTEXT_DIR},
            dockerfile={"inline": dockerfile},
            build_args={"MLFLOW_VERSION": args.get("mlflow_version")},
            push=True,
            tags=[
                pulumi.Output.format(
                    "{0}/mlflow-gcp:{1}",
                    mlflow_repo.registry_uri,
                    args.get("mlflow_version"),
                )
            ],
            registries=[
                docker_build.RegistryArgs(
                    address=pulumi.Output.format(
                        "{0}-docker.pkg.dev", args.get("region")
                    ),
                    username="oauth2accesstoken",
                    password=client_config.access_token,
                )
            ],
            opts=child_opts,
        )

        self.service = cloudrunv2.Service(
            name or "mlflow-service",
            opts=pulumi.ResourceOptions(
                parent=self,
                depends_on=[cloud_run_api],
            ),
            name=name or "mlflow-service",
            description="MLflow tracking server",
            location=args.get("region"),
            deletion_policy="DELETE",
            deletion_protection=False,
            ingress="INGRESS_TRAFFIC_ALL",
            invoker_iam_disabled=True,  # TODO: check options
            template={
                "containers": [
                    {
                        "image": mlflow_image.ref,
                        "commands": ["mlflow"],
                        "args": [
                            "server",
                            "--default-artifact-root",
                            args.get("bucket_url"),
                            "--host",
                            "0.0.0.0",
                            "--workers",
                            "2",
                            "--disable-security-middleware",
                        ],
                        "ports": {"container_port": 5000},
                        "envs": [
                            {
                                "name": "MLFLOW_BACKEND_STORE_URI",
                                "value_source": {
                                    "secret_key_ref": {
                                        "secret": args.get("backend_store_secret_id"),
                                        "version": "latest",
                                    },
                                },
                            },
                        ],
                        "resources": {
                            "cpu_idle": True,
                            "limits": {
                                "cpu": "1",  # TODO: check if customizable
                                "memory": "2Gi",  # TODO: check if customizable
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
                "health_check_disabled": True,  # TODO: check
                "service_account": args.get("sa_email"),
                "timeout": f"{args.get('timeout_seconds')}s",
            },
        )

        self.register_outputs(
            {
                "docker_image": mlflow_image.ref,
                "url": self.service.uri,
            }
        )
