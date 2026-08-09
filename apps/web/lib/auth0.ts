import { Auth0Client } from "@auth0/nextjs-auth0/server";

let client: Auth0Client | null = null;

export function oidcEnabled(): boolean {
  return process.env.AI_PLATFORM_AUTH_MODE === "oidc";
}

export function auth0Client(): Auth0Client {
  if (!oidcEnabled()) {
    throw new Error("Managed OIDC is not enabled for this deployment.");
  }
  const audience = process.env.AUTH0_AUDIENCE?.trim();
  if (!audience) {
    throw new Error("AUTH0_AUDIENCE is required when managed OIDC is enabled.");
  }
  client ??= new Auth0Client({
    authorizationParameters: {
      audience,
      scope: "openid profile email offline_access"
    },
    enableAccessTokenEndpoint: false
  });
  return client;
}
