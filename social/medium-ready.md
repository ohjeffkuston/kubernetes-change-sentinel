# Kubernetes Change Sentinel: Catching Risky Manifest Changes Before They Reach the Cluster

Kubernetes delivery moves quickly, but the most dangerous changes are often only a few lines long. A container gains privileged mode. A Role becomes cluster-wide. A Service becomes public. A replica reduction quietly removes resilience.

Those changes can pass a casual review because the manifest is syntactically valid and the deployment pipeline is healthy. The real question is not simply, “Will this apply?” It is, “Has this change altered the security or reliability boundary?”

![Kubernetes Change Sentinel architecture](https://raw.githubusercontent.com/ohjeffkuston/kubernetes-change-sentinel/main/docs/architecture.png)

## The problem

Kubernetes reviews mix many concerns: configuration correctness, security, availability, ownership, and deployment speed. Teams often depend on reviewers to notice every risky field by eye. That does not scale across many services and clusters.

An AI model can explain a diff, but it should not be the final authority for a production gate. Non-deterministic reasoning is useful for context, not for deciding whether a privileged workload or wildcard permission is acceptable.

## The solution

Kubernetes Change Sentinel is a deterministic, read-only policy engine. It accepts a before-and-after manifest bundle, identifies changed resources, evaluates high-risk patterns, and produces an auditable `PASS`, `REVIEW`, or `BLOCK` decision.

The project detects:

- privileged containers and `hostNetwork`;
- wildcard RBAC and new cluster-wide bindings;
- public load balancers;
- unpinned container images;
- missing CPU or memory limits;
- replica reductions and resource deletions.

Every finding has a stable code, severity, resource identity, and plain-language explanation. The same input always produces the same output.

## Architecture and safety boundary

The pipeline has four simple stages:

1. A CI job creates a before-and-after JSON bundle.
2. The sentinel normalizes each object by kind, namespace, and name.
3. The policy engine scores only changed, added, or deleted resources.
4. Non-passing decisions are routed to a human approver.

The engine never connects to Kubernetes, never receives a kubeconfig, and never calls `kubectl apply`. An optional n8n workflow can route completed reports, but it contains no cluster-write node.

## Why deterministic controls matter in AI-first operations

AI can help an engineer understand why a change is risky, relate it to a runbook, or prepare a review summary. The underlying decision should remain inspectable and testable.

That separation creates a safer pattern:

- policy code decides;
- AI explains;
- a human approves;
- a separate deployment system executes.

It is a small architecture choice with a large governance benefit.

## Testing the decision path

The repository includes unit tests for safe image changes, privileged containers, host networking, wildcard RBAC, replica reductions, deletions, deterministic output, and malformed duplicate resources. GitHub Actions validates the JSON artifacts and runs the full suite on every push.

## What I learned

The most valuable platform automation does not remove humans from every decision. It removes inconsistent detection and gives the human a clear, evidence-backed choice.

Kubernetes Change Sentinel is deliberately limited, but it demonstrates a production-minded principle: automate analysis aggressively while keeping high-impact authority explicit.

Source code: https://github.com/ohjeffkuston/kubernetes-change-sentinel

