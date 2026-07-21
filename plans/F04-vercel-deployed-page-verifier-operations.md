# F04 Vercel Deployed-Page Verifier Operations

## Scope

This runbook covers only the exact-SHA, deployment-protection-aware preview
verification used to repair `f04.deployed_page_verification`. It does not change
production traffic, branch aliases, the rollback-proof alias, project Git
integration, or deployment-protection policy.

## Required GitHub Actions secrets

- `VERCEL_AUTOMATION_BYPASS_SECRET` is owned by the Vercel project maintainers.
  It must be the active 32-character automation bypass configured for project
  `prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN` and must be supplied to GitHub through
  standard input. The value must never appear in commands, URLs, logs, evidence,
  pull requests, or issues.
- `VERCEL_API_TOKEN` is required because GitHub's deployment payload proves the
  exact SHA, provider, environment, success, and immutable hostname, but does not
  expose Vercel's canonical deployment ID, project ID, READY state, Git ref, and
  complete source metadata. The current credential uses existing team-authorized
  Vercel CLI access because that OAuth application is forbidden from creating a
  child token. Replace it with a dedicated, shorter-lived, team-scoped token when
  Vercel permits one to be created interactively.

The dedicated workflow reads both secrets only in the trusted same-repository
push job for `automation/f04-vercel-deployment-baseline`. It does not run on pull
requests or forks.

## Rotation and revocation

1. Generate a cryptographically random value matching Vercel's required
   32-character alphanumeric automation-bypass format without printing it.
2. Add the replacement through Vercel's supported project protection-bypass API
   or project settings, and make it active for the environment-variable header
   mechanism.
3. Pipe the same replacement to `gh secret set
   VERCEL_AUTOMATION_BYPASS_SECRET --body -` without command tracing.
4. Confirm only that the named GitHub secret exists and that exactly one intended
   Vercel automation bypass remains active; never read either value back.
5. Remove the superseded Vercel bypass immediately.

Rotate `VERCEL_API_TOKEN` in the token owner's Vercel account or team settings,
pipe the replacement to `gh secret set VERCEL_API_TOKEN --body -`, confirm only
secret-name presence, and revoke the superseded credential. If the credential is
suspected to be exposed, rotate and revoke before rerunning the workflow.

During this repair, a read-only inspection intended to show only bypass property
names exposed the previous bypass identifier in ephemeral tool output. The value
was treated as compromised: it was replaced in Vercel and GitHub, then revoked.
No value was written to Git, workflow logs, evidence, pull requests, or issues.

## Evidence handling

The verifier writes a new JSON file and fails if that path already exists. The
artifact contains deployment identity, exact Git metadata, bounded polling,
safe HTTP metadata, semantic assertions, and body/asset hashes. It excludes raw
HTML, response header collections, cookies, authorization material, bypass
values, API tokens, and temporary share URLs.
