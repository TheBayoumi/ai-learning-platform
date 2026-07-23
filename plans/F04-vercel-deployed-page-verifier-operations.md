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
  complete source metadata. The current credential is a dedicated one-day Vercel
  access token created interactively with the narrowest UI scope that includes
  the owning team (`Full Account`, non-SAML accounts). A personal-project scope
  was proven insufficient by HTTP 403 and was revoked. The credential expires on
  2026-07-22 and must be replaced before another run after that date. Vercel's
  CLI OAuth application was also proven unable to create a child token through
  the API.

The dedicated workflow reads both secrets only in the trusted same-repository
push job for `automation/f04-vercel-deployment-baseline`. It does not run on pull
requests or forks.

## Supported local invocation

Run the verifier from `apps/web`. On PowerShell, invoke the Windows command
shim explicitly so npm preserves every named argument after `--`:

```powershell
npm.cmd run verify:vercel-preview -- --expected-sha <exact-sha> --repository TheBayoumi/ai-learning-platform --branch automation/f04-vercel-deployment-baseline --project-id prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN --evidence-output <new-json-path>
```

Do not substitute `npm run` at a PowerShell prompt: when `npm` resolves to
`npm.ps1`, npm 11.18.0 strips the named option tokens in this invocation and the
verifier correctly rejects the remaining values as positional arguments. Bash,
including the dedicated Ubuntu workflow, uses the ordinary package-script form:

```bash
npm run verify:vercel-preview -- --expected-sha "$GITHUB_SHA" --repository TheBayoumi/ai-learning-platform --branch automation/f04-vercel-deployment-baseline --project-id prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN --evidence-output "$RUNNER_TEMP/f04-vercel-deployed-page-verification.json"
```

Evidence-only validation requires no credential. Use the same platform-specific
npm entrypoint and replace `--evidence-output` with `--validate-evidence
<json-path>`; all exact identity arguments remain required.

## Rotation and revocation

1. Generate a cryptographically random value matching Vercel's required
   32-character alphanumeric automation-bypass format without printing it.
2. Add the replacement through Vercel's supported project protection-bypass API
   or project settings, and make it active for the environment-variable header
   mechanism.
3. Pipe the same replacement to `gh secret set
   VERCEL_AUTOMATION_BYPASS_SECRET` through standard input, without command
   tracing. Do not pass `--body -`; that stores a literal hyphen rather than
   reading standard input.
4. Confirm only that the named GitHub secret exists and that exactly one intended
   Vercel automation bypass remains active; never read either value back.
5. Remove the superseded Vercel bypass immediately.

Rotate `VERCEL_API_TOKEN` in the token owner's Vercel account or team settings,
pipe the replacement through standard input to `gh secret set VERCEL_API_TOKEN`
without `--body`, confirm only secret-name presence, and revoke the superseded
credential. If the credential is suspected to be exposed, rotate and revoke
before rerunning the workflow.

During this repair, two read-only inspections intended to show only bypass
metadata exposed superseded bypass values in ephemeral tool output. Each value
was treated as compromised and revoked immediately. A final unexposed bypass was
made the system environment value and stored in GitHub through standard input.
No bypass value was written to Git, workflow logs, evidence, pull requests, or
issues.

## Evidence handling

The verifier writes a new JSON file and fails if that path already exists. The
artifact contains deployment identity, exact Git metadata, bounded polling,
safe HTTP metadata, semantic assertions, and body/asset hashes. It excludes raw
HTML, response header collections, cookies, authorization material, bypass
values, API tokens, and temporary share URLs.
