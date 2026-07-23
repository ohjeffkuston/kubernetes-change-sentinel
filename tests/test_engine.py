import copy
import unittest

from kubernetes_change_sentinel.engine import review_change


def deployment(name="api", image="example/api:1.2.3", replicas=2, privileged=False):
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name, "namespace": "prod"},
        "spec": {
            "replicas": replicas,
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "api",
                            "image": image,
                            "securityContext": {"privileged": privileged},
                            "resources": {
                                "limits": {"cpu": "500m", "memory": "512Mi"}
                            },
                        }
                    ]
                }
            },
        },
    }


class ReviewChangeTests(unittest.TestCase):
    def test_safe_pinned_change_passes(self):
        old = deployment(image="example/api:1.2.2")
        new = deployment(image="example/api:1.2.3")
        self.assertEqual("PASS", review_change({"before": [old], "after": [new]})["decision"])

    def test_privileged_container_blocks(self):
        report = review_change({"before": [], "after": [deployment(privileged=True)]})
        self.assertEqual("BLOCK", report["decision"])
        self.assertIn("PRIVILEGED_CONTAINER", [item["code"] for item in report["findings"]])

    def test_host_network_blocks(self):
        item = deployment()
        item["spec"]["template"]["spec"]["hostNetwork"] = True
        self.assertEqual("BLOCK", review_change({"before": [], "after": [item]})["decision"])

    def test_wildcard_cluster_role_blocks(self):
        role = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRole",
            "metadata": {"name": "danger"},
            "rules": [{"apiGroups": ["*"], "resources": ["*"], "verbs": ["*"]}],
        }
        report = review_change({"before": [], "after": [role]})
        self.assertEqual("RBAC_WILDCARD", report["findings"][0]["code"])

    def test_replica_reduction_requires_review(self):
        report = review_change(
            {"before": [deployment(replicas=3)], "after": [deployment(replicas=1)]}
        )
        self.assertEqual("REVIEW", report["decision"])
        self.assertEqual("REPLICA_REDUCTION", report["findings"][0]["code"])

    def test_deletion_requires_review(self):
        report = review_change({"before": [deployment()], "after": []})
        self.assertEqual("REVIEW", report["decision"])
        self.assertEqual(1, report["summary"]["resources_deleted"])

    def test_output_is_deterministic_and_input_unchanged(self):
        payload = {"before": [], "after": [deployment(image="example/api:latest")]}
        original = copy.deepcopy(payload)
        self.assertEqual(review_change(payload), review_change(payload))
        self.assertEqual(original, payload)

    def test_duplicate_identity_fails_closed(self):
        item = deployment()
        with self.assertRaisesRegex(ValueError, "duplicate manifest identity"):
            review_change({"before": [], "after": [item, copy.deepcopy(item)]})


if __name__ == "__main__":
    unittest.main()

