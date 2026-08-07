"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";

import { publishPlanSaved, publishPlanUpdated } from "../../lib/learning-events";
import { LEARNING_SESSION_STORAGE_KEY } from "../../lib/learning-session";
import { loadRoles, resumePlan } from "../../lib/platform-client";
import type { PlanView, RoleView } from "../../lib/learning-contract";

interface AppContextValue {
  readonly roles: readonly RoleView[];
  readonly plan: PlanView | null;
  readonly loading: boolean;
  readonly error: string | null;
  readonly commitPlan: (plan: PlanView) => void;
  readonly clearPlan: () => void;
  readonly reload: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [roles, setRoles] = useState<readonly RoleView[]>([]);
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const commitPlan = useCallback((nextPlan: PlanView) => {
    setPlan(nextPlan);
    window.localStorage.setItem(LEARNING_SESSION_STORAGE_KEY, nextPlan.state_token);
    publishPlanSaved();
    publishPlanUpdated(nextPlan);
  }, []);

  const clearPlan = useCallback(() => {
    window.localStorage.removeItem(LEARNING_SESSION_STORAGE_KEY);
    setPlan(null);
    setError(null);
    publishPlanSaved();
  }, []);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const roleList = await loadRoles();
      setRoles(roleList);
      const token = window.localStorage.getItem(LEARNING_SESSION_STORAGE_KEY);
      if (token !== null) {
        const resumed = await resumePlan(token);
        setPlan(resumed);
        window.localStorage.setItem(LEARNING_SESSION_STORAGE_KEY, resumed.state_token);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The learning workspace could not load.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [reload]);

  const value = useMemo<AppContextValue>(
    () => ({ roles, plan, loading, error, commitPlan, clearPlan, reload }),
    [clearPlan, commitPlan, error, loading, plan, reload, roles]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useCareerApp(): AppContextValue {
  const value = useContext(AppContext);
  if (value === null) {
    throw new Error("useCareerApp must be used inside AppProvider");
  }
  return value;
}
