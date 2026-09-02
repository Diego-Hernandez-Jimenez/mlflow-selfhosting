import unittest

import pulumi
from components.iam import IamArgs, MlflowIam

from tests.mocks import MyMocks


class TestMlflowIam(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mocks = MyMocks()
        pulumi.runtime.set_mocks(self.mocks, preview=False)
        self.iam = MlflowIam(
            "test-iam",
            IamArgs(
                bucket_name="test-bucket",
                backend_store_uri_secret_id="test-secret",
            ),
        )

    @pulumi.runtime.test
    def test_bucket_iam_binding_grants_object_user(self):
        """Bucket IAM binding must grant roles/storage.objectUser to the service account."""

        def check(role):
            self.assertEqual(role, "roles/storage.objectUser")

        return self.iam.bucket_binding.role.apply(check)

    @pulumi.runtime.test
    def test_secret_iam_member_grants_secret_accessor(self):
        """Secret IAM member must grant roles/secretmanager.secretAccessor to the service account."""

        def check(role):
            self.assertEqual(role, "roles/secretmanager.secretAccessor")

        return self.iam.secret_member.role.apply(check)
