"""Deterministic, read-only risk analysis for Kubernetes manifest changes."""

from __future__ import annotations

from collections import Counter
from typing import Any

SEVERITY_WEIGHT = {"critical": 30, "high": 15, "medium": 7, "low": 3}
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "Pod"}


def _identity(manifest: dict[str, Any]) -> tuple[str, str, str]:
    metadata = manifest.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("manifest.metadata must be an object")
    kind = str(manifest.get("kind", "")).strip()
    namespace = str(metadata.get("namespace", "default")).strip() or "default"
    name = str(metadata.get("name", "")).strip()
    if not kind or not name:
        raise ValueError("every manifest requires kind and metadata.name")
    return kind, namespace, name


def _index(manifests: Any, field: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    if not isinstance(manifests, list):
        raise ValueError(f"{field} must be a list")
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for position, manifest in enumerate(manifests):
        if not isinstance(manifest, dict):
            raise ValueError(f"{field}[{position}] must be an object")
        identity = _identity(manifest)
        if identity in result:
            raise ValueError(f"duplicate manifest identity in {field}: {'/'.join(identity)}")
        result[identity] = manifest
    return result


def _pod_spec(manifest: dict[str, Any]) -> dict[str, Any]:
    spec = manifest.get("spec", {})
    if not isinstance(spec, dict):
        return {}
    kind = str(manifest.get("kind", ""))
    if kind == "Pod":
        return spec
    if kind == "CronJob":
        return (
            spec.get("jobTemplate", {})
            .get("spec", {})
            .get("template", {})
            .get("spec", {})
        )
    if kind in WORKLOAD_KINDS:
        return spec.get("template", {}).get("spec", {})
    return {}


def _finding(
    identity: tuple[str, str, str],
    code: str,
    severity: str,
    message: str,
) -> dict[str, str]:
    kind, namespace, name = identity
    return {
        "resource": f"{namespace}/{kind}/{name}",
        "code": code,
        "severity": severity,
        "message": message,
    }


def _container_findings(
    identity: tuple[str, str, str],
    manifest: dict[str, Any],
) -> list[dict[str, str]]:
    pod_spec = _pod_spec(manifest)
    findings: list[dict[str, str]] = []
    if not isinstance(pod_spec, dict) or not pod_spec:
        return findings
    if pod_spec.get("hostNetwork") is True:
        findings.append(
            _finding(identity, "HOST_NETWORK_ENABLED", "critical", "Workload enables hostNetwork.")
        )
    containers = pod_spec.get("containers", [])
    if not isinstance(containers, list):
        raise ValueError("pod spec containers must be a list")
    for container in containers:
        if not isinstance(container, dict):
            raise ValueError("each container must be an object")
        name = str(container.get("name", "unnamed"))
        security = container.get("securityContext", {})
        if isinstance(security, dict) and security.get("privileged") is True:
            findings.append(
                _finding(
                    identity,
                    "PRIVILEGED_CONTAINER",
                    "critical",
                    f"Container '{name}' enables privileged mode.",
                )
            )
        image = str(container.get("image", ""))
        if image.endswith(":latest") or (image and ":" not in image.rsplit("/", 1)[-1]):
            findings.append(
                _finding(
                    identity,
                    "UNPINNED_IMAGE",
                    "medium",
                    f"Container '{name}' uses an unpinned image tag.",
                )
            )
        resources = container.get("resources", {})
        limits = resources.get("limits", {}) if isinstance(resources, dict) else {}
        if not isinstance(limits, dict) or not limits.get("cpu") or not limits.get("memory"):
            findings.append(
                _finding(
                    identity,
                    "RESOURCE_LIMITS_MISSING",
                    "medium",
                    f"Container '{name}' is missing CPU or memory limits.",
                )
            )
    return findings


def _rbac_findings(
    identity: tuple[str, str, str],
    manifest: dict[str, Any],
) -> list[dict[str, str]]:
    kind = identity[0]
    findings: list[dict[str, str]] = []
    if kind == "ClusterRoleBinding":
        findings.append(
            _finding(
                identity,
                "CLUSTER_ROLE_BINDING_CHANGED",
                "critical",
                "A cluster-wide role binding is added or changed.",
            )
        )
    if kind in {"Role", "ClusterRole"}:
        rules = manifest.get("rules", [])
        if not isinstance(rules, list):
            raise ValueError("RBAC rules must be a list")
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError("each RBAC rule must be an object")
            verbs = rule.get("verbs", [])
            resources = rule.get("resources", [])
            if "*" in verbs or "*" in resources:
                findings.append(
                    _finding(
                        identity,
                        "RBAC_WILDCARD",
                        "critical",
                        "RBAC rule grants wildcard verbs or resources.",
                    )
                )
                break
    return findings


def _change_findings(
    identity: tuple[str, str, str],
    before: dict[str, Any] | None,
    after: dict[str, Any],
) -> list[dict[str, str]]:
    findings = _container_findings(identity, after) + _rbac_findings(identity, after)
    kind = identity[0]
    if kind == "Service" and after.get("spec", {}).get("type") == "LoadBalancer":
        old_type = before.get("spec", {}).get("type") if before else None
        if old_type != "LoadBalancer":
            findings.append(
                _finding(
                    identity,
                    "PUBLIC_LOAD_BALANCER",
                    "high",
                    "Change introduces a LoadBalancer service.",
                )
            )
    if kind in {"Deployment", "StatefulSet"} and before:
        old_replicas = before.get("spec", {}).get("replicas", 1)
        new_replicas = after.get("spec", {}).get("replicas", 1)
        if isinstance(old_replicas, int) and isinstance(new_replicas, int) and new_replicas < old_replicas:
            findings.append(
                _finding(
                    identity,
                    "REPLICA_REDUCTION",
                    "high" if new_replicas == 0 else "medium",
                    f"Replica count decreases from {old_replicas} to {new_replicas}.",
                )
            )
    return findings


def review_change(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a stable approval risk report without applying any change."""
    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")
    before = _index(payload.get("before", []), "before")
    after = _index(payload.get("after"), "after")
    deleted = sorted(set(before) - set(after))
    findings: list[dict[str, str]] = []

    for identity in sorted(after):
        old = before.get(identity)
        if old == after[identity]:
            continue
        findings.extend(_change_findings(identity, old, after[identity]))

    for identity in deleted:
        findings.append(
            _finding(identity, "RESOURCE_DELETED", "high", "Resource is removed by this change.")
        )

    findings.sort(key=lambda item: (item["resource"], item["code"]))
    counts = Counter(item["severity"] for item in findings)
    penalty = sum(SEVERITY_WEIGHT[item["severity"]] for item in findings)
    score = max(0, 100 - penalty)
    if counts["critical"]:
        decision = "BLOCK"
    elif findings:
        decision = "REVIEW"
    else:
        decision = "PASS"
    changed = sum(1 for key, value in after.items() if before.get(key) != value)

    return {
        "project": "Kubernetes Change Sentinel",
        "decision": decision,
        "risk_score": score,
        "summary": {
            "resources_before": len(before),
            "resources_after": len(after),
            "resources_changed_or_added": changed,
            "resources_deleted": len(deleted),
            "findings": len(findings),
            "severity_counts": {
                level: counts[level] for level in ("critical", "high", "medium", "low")
            },
        },
        "findings": findings,
        "safety": {
            "mode": "read_only",
            "cluster_connection": False,
            "manifest_applied": False,
            "human_approval_required": decision != "PASS",
        },
    }

