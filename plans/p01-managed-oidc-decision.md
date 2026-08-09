# P01 Managed OIDC Decision

## Status

Provisional implementation selection. The approved architectural boundary remains **Managed OIDC** with provider-neutral domain account mappings.

## Selected launch provider

Auth0 is the provisional launch provider for the adult B2C web product.

Selection evidence checked on 2026-08-09:

- Auth0's current B2C Free plan advertises up to 25,000 monthly active users, which keeps the validation-stage identity cost at zero while usage is small.
- Auth0 publishes an official Next.js v4 integration for server-managed sessions and `/auth/*` login/logout/callback routes.
- Auth0 publishes a FastAPI API quickstart for RS256 access-token validation.
- The application will not persist Auth0 user IDs as domain account IDs. PostgreSQL stores a stable platform account UUID plus an OIDC issuer/subject mapping.

## Replacement boundary

Provider-specific browser/session code is isolated under the web authentication adapter. Backend authorization consumes standard OIDC access-token claims through an issuer/audience/JWKS verifier. Domain services receive a stable platform account identity and role set; they never receive Auth0 SDK objects.

Changing provider therefore requires replacing configuration and the web login/session adapter while retaining:

- `accounts.id` platform UUIDs;
- issuer/subject mappings;
- role/permission rules;
- learner-state ownership;
- evidence history;
- artifact ownership; and
- authorization tests.

## Required production configuration

The production environment must eventually supply the managed-provider tenant/application values and secrets. Until those are configured and the live sign-in/callback/session/cross-device canary succeeds, P01 cannot be marked PASSED.

## Failure policy

Missing or invalid OIDC configuration fails closed in production. Invalid, expired, wrong-issuer, wrong-audience, unsupported-algorithm, or unknown-key access tokens are unauthorized. Browser-provided account identifiers are not authoritative once OIDC mode is enabled. Anonymous-account migration is a one-time authenticated claim operation and cannot be used to select another authenticated account.
