import type { PlanView } from "./learning-contract";

export const PLAN_SAVED_EVENT = "career-atlas:plan-saved";
export const PLAN_UPDATED_EVENT = "career-atlas:plan-updated";

export interface PlanUpdatedDetail {
  readonly plan: PlanView;
}

export function publishPlanSaved(): void {
  window.dispatchEvent(new Event(PLAN_SAVED_EVENT));
}

export function publishPlanUpdated(plan: PlanView): void {
  window.dispatchEvent(
    new CustomEvent<PlanUpdatedDetail>(PLAN_UPDATED_EVENT, {
      detail: { plan }
    })
  );
}
