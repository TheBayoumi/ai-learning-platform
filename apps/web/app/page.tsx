import { PlatformShell } from "../components/platform-shell";
import { resolveRuntimeApiAvailability } from "../server/health/runtime-health";

export const dynamic = "force-dynamic";

export const preferredRegion = "pdx1";

export default async function HomePage() {
  const apiAvailability = await resolveRuntimeApiAvailability();
  return <PlatformShell apiAvailability={apiAvailability} />;
}
