# Day 7 — Kubernetes Change Sentinel

To: ohjeffkuston@yahoo.ca

Hi Jeffrey,

Today’s project is **Kubernetes Change Sentinel**, a deterministic, read-only approval gate for Kubernetes manifest changes.

## What problem it solves

Small manifest edits can create large security or reliability risks. A release may introduce privileged execution, host networking, wildcard RBAC, a public load balancer, an unpinned image, missing resource limits, or a replica reduction. The project makes those risks explicit before a deployment system touches a cluster.

## Architecture

1. CI or a developer supplies a JSON bundle containing `before` and `after` manifests.
2. The engine indexes objects by kind, namespace, and name.
3. It evaluates only changed, added, and deleted resources.
4. It emits an explainable `PASS`, `REVIEW`, or `BLOCK` report.
5. n8n can route non-passing reports for human approval.

The safety boundary is intentional: no cluster connection, no kubeconfig, no credentials, and no autonomous remediation.

## How the engine works

`review_change()` validates the input, detects duplicate identities, compares the resource sets, and runs focused policy checks. Critical findings such as privileged containers, host networking, wildcard RBAC, or a ClusterRoleBinding produce `BLOCK`. High or medium findings such as deletions, new load balancers, replica reductions, unpinned images, or missing limits produce `REVIEW`.

Every result includes a risk score, severity totals, stable finding codes, and the affected resource.

## Run it locally

```bash
cd day-07-kubernetes-change-sentinel
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m kubernetes_change_sentinel examples/change-request.json
```

The CLI exit codes make the result easy to use in CI:

- `0` = PASS
- `1` = REVIEW
- `2` = BLOCK

## Deploy it safely

1. Run the sentinel in a pull-request workflow before the GitOps or deployment job.
2. Generate the before/after bundle from version-controlled manifests.
3. Store no kubeconfig or production token in the sentinel job.
4. Make `BLOCK` stop the pipeline.
5. Route `REVIEW` to a protected environment or approval workflow.
6. Keep the actual deployment in a different job with its own least-privilege credentials.

## What to study

- Kubernetes workload and pod specs.
- RBAC resources: Role, ClusterRole, RoleBinding, and ClusterRoleBinding.
- Security contexts and why privileged containers are dangerous.
- Resource requests/limits and availability risks.
- GitOps approval patterns.
- The difference between deterministic policy and AI-generated explanation.

## Interview positioning

Use this project to explain that you can combine Kubernetes, DevSecOps, CI/CD, policy-as-code, n8n orchestration, testing, and AI-safe governance. A strong interview explanation is:

> I built a deterministic pre-deployment gate that analyzes Kubernetes changes without cluster credentials. The policy engine makes the decision, AI can explain the evidence, and humans retain approval for high-impact actions.

That answer demonstrates technical implementation and mature operational judgement.

## Practice exercises

1. Add a rule for host-path volumes.
2. Add a policy configuration file so teams can tune severities.
3. Generate the before/after bundle from Helm-rendered manifests.
4. Publish reports as pull-request checks.
5. Add an AI summary that is forbidden from changing the deterministic decision.

Repository: https://github.com/ohjeffkuston/kubernetes-change-sentinel

Best,

Your Cloud + AI Portfolio Automation

