Imagine a routine Kubernetes release that quietly introduces a privileged container and a wildcard ClusterRole.

The pull request looks small. The service still deploys. But the blast radius has changed—and the organization may not discover it until an incident, audit, or compromise.

For enterprises running many clusters and delivery pipelines, change review is not just a deployment concern. It is a security and governance control. Risky manifests can expand network access, bypass isolation, remove resource safeguards, or grant cluster-wide privileges.

I built Kubernetes Change Sentinel to turn before-and-after manifests into a deterministic, explainable approval decision before anything reaches a cluster.

- Detects privileged containers, host networking, and cluster-wide RBAC changes.
- Flags wildcard permissions, public load balancers, and unpinned images.
- Identifies replica reductions, resource deletions, and missing CPU or memory limits.
- Produces stable PASS, REVIEW, or BLOCK decisions for CI and n8n workflows.
- Keeps deployment authority with a human: no cluster credentials and no autonomous remediation.

This pattern is game-changing because it separates AI-assisted explanation from the policy decision. Teams can move quickly without giving an agent permission to change production.

Which Kubernetes change would you always require a human to approve?

Follow my profile for practical Cloud, DevOps, and AI-first engineering projects.

#Kubernetes #DevSecOps #PlatformEngineering #CloudSecurity #AIOrchestration

