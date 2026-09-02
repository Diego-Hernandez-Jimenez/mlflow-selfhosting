import os
import unittest
from unittest import mock

import pulumi
from components.backend_store import BackendStore, BackendStoreArgs, PgVersion

from tests.mocks import MyMocks


class TestBackendStore(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mocks = MyMocks()
        pulumi.runtime.set_mocks(self.mocks, preview=False)
        with mock.patch.dict(os.environ, {"NEON_ORGANIZATION_ID": "test-org-123"}):
            self.backend = BackendStore(
                "test-backend",
                BackendStoreArgs(
                    project_name="test-mlflow-project",
                    branch_name="dev",
                    pg_version=PgVersion.PG17,
                    region_id="aws-us-east-1",
                ),
            )

    @pulumi.runtime.test
    def test_connection_uri_uses_postgresql_scheme(self):
        """Backend URI must replace postgres:// with postgresql:// for MLflow compatibility."""

        def check(uri):
            self.assertIn("postgresql://", uri, "URI must use postgresql:// scheme")
            self.assertNotIn(
                "postgres://", uri, "URI must not contain the bare postgres:// scheme"
            )

        return self.backend.backend_store_uri.apply(check)

    @pulumi.runtime.test
    def test_secret_created_for_backend_store_uri(self):
        """A Secret Manager secret must be created to store the DB connection URI."""

        def check(_):
            secrets = self.mocks.find_resources("secretmanager/secret:Secret")
            self.assertEqual(len(secrets), 1, "Expected exactly 1 Secret resource")

        return self.backend.backend_store_uri_secret.secret_id.apply(check)
