"""Apply the assessment-to-dashboard browser synchronization before verification."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "apps/web/components/learning-platform.tsx"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} count was {count}, expected 1")
    return text.replace(old, new, 1)


def main() -> None:
    text = COMPONENT.read_text(encoding="utf-8")
    if "PLAN_UPDATED_EVENT" in text:
        return

    text = replace_once(
        text,
        '} from "../lib/learning-contract";\n\nconst SESSION_STORAGE_KEY = "ai-career-learning-plan-v1";\n',
        '} from "../lib/learning-contract";\n'
        'import {\n'
        '  PLAN_UPDATED_EVENT,\n'
        '  publishPlanSaved,\n'
        '  type PlanUpdatedDetail\n'
        '} from "../lib/learning-events";\n'
        'import { LEARNING_SESSION_STORAGE_KEY } from "../lib/learning-session";\n',
        "learning event imports",
    )
    text = text.replace("SESSION_STORAGE_KEY", "LEARNING_SESSION_STORAGE_KEY")
    text = replace_once(
        text,
        "    window.localStorage.setItem(LEARNING_SESSION_STORAGE_KEY, nextPlan.state_token);\n",
        "    window.localStorage.setItem(LEARNING_SESSION_STORAGE_KEY, nextPlan.state_token);\n"
        "    publishPlanSaved();\n",
        "plan saved publication",
    )
    load_effect = '''  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadPlatform();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [loadPlatform]);
'''
    update_effect = '''  useEffect(() => {
    const handlePlanUpdated = (event: Event) => {
      if (!(event instanceof CustomEvent)) {
        return;
      }
      const detail = event.detail as PlanUpdatedDetail | undefined;
      if (detail !== undefined && isPlanView(detail.plan)) {
        storePlan(detail.plan);
      }
    };
    window.addEventListener(PLAN_UPDATED_EVENT, handlePlanUpdated);
    return () => window.removeEventListener(PLAN_UPDATED_EVENT, handlePlanUpdated);
  }, [storePlan]);

'''
    text = replace_once(
        text,
        load_effect,
        load_effect + "\n" + update_effect,
        "plan update listener",
    )
    COMPONENT.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
