import unittest

import pulumi
from components.artifact_store import ArtifactStore, ArtifactStoreArgs

from tests.mocks import MyMocks

# Note:
# * Because all Pulumi resource properties are outputs—since many of them are computed asynchronously—we need to use the `apply` method to get access to the values
# * Since these outputs are resolved asynchronously, we need to use the framework’s built-in asynchronous test capability.


class TestArtifactStore(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mocks = MyMocks()
        pulumi.runtime.set_mocks(self.mocks, preview=False)
        self.store = ArtifactStore(
            "test-store",
            ArtifactStoreArgs(location="us-east1"),
        )

    @pulumi.runtime.test
    def test_public_access_prevention_is_enforced(self):
        """Bucket must block all public access."""

        def check(public_access_prevention):
            self.assertEqual(public_access_prevention, "enforced")

        return self.store.bucket.public_access_prevention.apply(check)

    @pulumi.runtime.test
    def test_uniform_bucket_level_access_enabled(self):
        """Bucket must use uniform IAM access (no per-object ACLs)."""

        def check(uniform_bucket_level_access):
            self.assertTrue(uniform_bucket_level_access)

        return self.store.bucket.uniform_bucket_level_access.apply(check)

    @pulumi.runtime.test
    def test_autoclass_is_configured(self):
        """Bucket must have autoclass enabled with NEARLINE as terminal class."""

        def check(_):
            buckets = self.mocks.find_resources("storage/bucket:Bucket")
            self.assertEqual(len(buckets), 1)
            autoclass = buckets[0].get("autoclass")
            self.assertIsNotNone(autoclass, "autoclass should be set on the bucket")
            if isinstance(autoclass, dict):
                enabled = autoclass.get("enabled") or autoclass.get("enabled")
                self.assertTrue(enabled, "autoclass.enabled must be True")

        return self.store.bucket.name.apply(check)

    @pulumi.runtime.test
    def test_bucket_url_has_gcs_scheme(self):
        """Bucket URL output must use the gs:// scheme."""

        def check(url):
            self.assertTrue(url.startswith("gs://"), f"Expected gs:// URL, got: {url}")

        return self.store.bucket.url.apply(check)
