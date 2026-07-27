# Infrastructure as code

<!-- summary: Declarative, reviewed, no click-ops; managed state, env parity, least-privilege, plan-before-apply. -->
<!-- tier: domain -->
<!-- category: DevOps & Platform -->

Infrastructure is code, and gets the same discipline: version-controlled,
reviewed, and reproducible. A resource that exists only because someone clicked
a console is undocumented, un-reviewable, and gone the day they leave.

**Declarative and in the repo.** Infrastructure is defined as code (Terraform,
Pulumi, CloudFormation, Kubernetes manifests, …), committed, and changed through
the same review + CI path as application code. No click-ops for anything that
matters.

**Plan before apply.** Every change produces a plan/diff a human reads before it
is applied. Applies run from CI against reviewed code, not from a laptop.

**Managed, locked state.** Remote, locked, backed-up state — never local state
files, never state committed to git. Concurrent applies must not corrupt it.

**Environment parity.** Staging mirrors production in shape (same modules,
different sizes/counts), so what you test is what you ship. Differences are
parameters, not divergent hand-built stacks.

**Least-privilege, everywhere.** IAM roles, security groups, and service
accounts grant the minimum needed. Default-deny; open specific paths
deliberately. The pipeline's own credentials are scoped and short-lived.

**Secrets never live in the code.** Pull them from a secrets manager or
injected variables (see secure-by-default), never hardcoded in a manifest or
committed tfvars.

**Immutable over mutated.** Replace infrastructure rather than hand-patching
running instances, so the code stays the truth and drift can't accumulate.
