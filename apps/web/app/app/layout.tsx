import type { ReactNode } from "react";

import { AppProvider } from "../../components/app/app-provider";
import { AppShell } from "../../components/app/app-shell";

export const dynamic = "force-dynamic";
export const preferredRegion = "pdx1";

export default function LearningAppLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <AppProvider>
      <AppShell>{children}</AppShell>
    </AppProvider>
  );
}
