import pulumi


class MyMocks(pulumi.runtime.Mocks):
    """Records all resources created during a Pulumi program run for assertions."""

    def __init__(self):
        self.resources: list[tuple[str, str, dict]] = []  # (typ, name, outputs)

    def new_resource(self, args: pulumi.runtime.MockResourceArgs):
        outputs = dict(args.inputs)

        if "storage/bucket:Bucket" in args.typ:
            outputs.setdefault("name", args.name)
            outputs.setdefault("url", f"gs://{args.name}")
        elif "neon:index/project:Project" in args.typ:
            outputs.setdefault(
                "connectionUriPooler",
                "postgres://user:pass@host/mlflow-backend-store",
            )
            outputs.setdefault("databaseName", "mlflow-backend-store")
            outputs.setdefault("id", args.name + "_id")
        elif "serviceaccount" in args.typ.lower() and "account:Account" in args.typ:
            outputs.setdefault("accountId", "mlflow-sa")
            outputs.setdefault(
                "email", "mlflow-sa@test-project.iam.gserviceaccount.com"
            )
            outputs.setdefault(
                "member",
                "serviceAccount:mlflow-sa@test-project.iam.gserviceaccount.com",
            )
        elif "cloudrunv2/service:Service" in args.typ:
            outputs.setdefault("uri", f"https://{args.name}-abc123-uc.a.run.app")
        elif "secretmanager/secret:Secret" in args.typ:
            outputs.setdefault("secretId", outputs.get("secretId", args.name))

        self.resources.append((args.typ, args.name, outputs))

        # Handle all other resources
        return [args.name + "_id", outputs]

    def call(self, args: pulumi.runtime.MockCallArgs):
        return {}

    def find_resources(self, type_fragment: str) -> list[dict]:
        """Returns outputs of all resources whose type contains type_fragment."""
        return [outputs for typ, _, outputs in self.resources if type_fragment in typ]
