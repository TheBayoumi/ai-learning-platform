"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";

import { readPlatformError } from "../lib/learning-contract";
import { PLAN_SAVED_EVENT } from "../lib/learning-events";
import { LEARNING_SESSION_STORAGE_KEY } from "../lib/learning-session";
import { parseTutorFrames, type TutorStreamEvent } from "../lib/tutor-stream";
import styles from "./tutor-panel.module.css";

type TutorMove = "explain" | "hint" | "review";
type TutorRole = "user" | "assistant";

interface TutorMessage {
  readonly role: TutorRole;
  readonly content: string;
}

export function TutorPanel() {
  const [hasPlan, setHasPlan] = useState(false);
  const [move, setMove] = useState<TutorMove>("hint");
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<readonly TutorMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () => {
      setHasPlan(window.localStorage.getItem(LEARNING_SESSION_STORAGE_KEY) !== null);
    };
    const handle = window.setTimeout(refresh, 0);
    window.addEventListener(PLAN_SAVED_EVENT, refresh);
    return () => {
      window.clearTimeout(handle);
      window.removeEventListener(PLAN_SAVED_EVENT, refresh);
    };
  }, []);

  const canSend = useMemo(
    () => hasPlan && !busy && draft.trim().length > 0,
    [busy, draft, hasPlan]
  );

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const stateToken = window.localStorage.getItem(LEARNING_SESSION_STORAGE_KEY);
    const message = draft.trim();
    if (stateToken === null) {
      setHasPlan(false);
      setError("Create or resume a learning plan before opening a tutor turn.");
      return;
    }
    if (message === "") {
      return;
    }

    const history = messages.slice(-6);
    setMessages((current) => [
      ...current,
      { role: "user", content: message },
      { role: "assistant", content: "" }
    ]);
    setDraft("");
    setBusy(true);
    setError(null);
    try {
      await streamTutor(
        {
          state_token: stateToken,
          message,
          move,
          history
        },
        (streamEvent) => {
          if (streamEvent.event === "meta") {
            setModel(streamEvent.data.model);
          } else if (streamEvent.event === "delta") {
            appendAssistantDelta(streamEvent.data.text, setMessages);
          } else if (streamEvent.event === "error") {
            throw new Error(streamEvent.data.message);
          }
        }
      );
    } catch (caught) {
      setMessages((current) =>
        current.at(-1)?.role === "assistant" && current.at(-1)?.content === ""
          ? current.slice(0, -1)
          : current
      );
      setError(
        caught instanceof Error
          ? caught.message
          : "The tutor turn could not be completed."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={styles.workspace} aria-labelledby="tutor-heading">
      <header className={styles.header}>
        <div>
          <p className="eyebrow">Bounded AI coaching</p>
          <h2 id="tutor-heading">Ask for the next useful move, not a fake pass.</h2>
          <p>
            The tutor receives a minimized view of your current mission. It can explain, hint,
            and review, but it cannot change mastery, accept evidence, or certify readiness.
          </p>
        </div>
        <div className={styles.policy} aria-label="Tutor boundaries">
          <span>Browser-only conversation</span>
          <span>600-token response ceiling</span>
          <span>No state authority</span>
        </div>
      </header>

      {!hasPlan ? (
        <div className={styles.empty}>
          <strong>Create your adaptive learning plan first.</strong>
          <p>The tutor is tied to the exact current activity and priority gaps.</p>
        </div>
      ) : (
        <div className={styles.layout}>
          <div className={styles.transcript} aria-live="polite">
            {messages.length === 0 ? (
              <div className={styles.emptyTranscript}>
                <strong>Start with the blocker in front of you.</strong>
                <p>Do not paste passwords, API keys, private source, or employer data.</p>
              </div>
            ) : (
              <ol>
                {messages.map((message, index) => (
                  <li
                    className={message.role === "user" ? styles.user : styles.assistant}
                    key={`${message.role}-${index}`}
                  >
                    <span>{message.role === "user" ? "You" : "Tutor"}</span>
                    <p>{message.content || (busy ? "Thinking…" : "")}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>

          <form className={styles.composer} onSubmit={submit}>
            <label htmlFor="tutor-move">Tutor move</label>
            <select
              id="tutor-move"
              value={move}
              onChange={(event) => setMove(event.target.value as TutorMove)}
            >
              <option value="hint">Hint · one next step</option>
              <option value="explain">Explain · concept and example</option>
              <option value="review">Review · critique supplied work</option>
            </select>

            <label htmlFor="tutor-message">Question or work excerpt</label>
            <textarea
              id="tutor-message"
              rows={5}
              minLength={1}
              maxLength={2_000}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Example: My FastAPI dependency returns a session directly. What lifetime problem should I check first?"
            />
            <div className={styles.actions}>
              <button className="button button-primary" type="submit" disabled={!canSend}>
                {busy ? "Tutor responding…" : "Ask the tutor"}
              </button>
              <button
                className="button button-quiet"
                type="button"
                disabled={busy || messages.length === 0}
                onClick={() => {
                  setMessages([]);
                  setError(null);
                  setModel(null);
                }}
              >
                Clear conversation
              </button>
            </div>
            {model !== null ? <small>Model route: {model}</small> : null}
          </form>
        </div>
      )}

      {error !== null ? (
        <div className="error-banner" role="alert">
          <p>{error}</p>
        </div>
      ) : null}
    </section>
  );
}

async function streamTutor(
  body: Readonly<{
    state_token: string;
    message: string;
    move: TutorMove;
    history: readonly TutorMessage[];
  }>,
  onEvent: (event: TutorStreamEvent) => void
): Promise<void> {
  const response = await fetch("/api/platform/tutor/stream", {
    method: "POST",
    headers: {
      accept: "text/event-stream",
      "content-type": "application/json"
    },
    body: JSON.stringify(body),
    cache: "no-store",
    credentials: "same-origin"
  });
  if (!response.ok) {
    let value: unknown;
    try {
      value = await response.json();
    } catch {
      throw new Error("The tutor service returned an unreadable response.");
    }
    throw new Error(readPlatformError(value));
  }
  if (!response.headers.get("content-type")?.toLowerCase().startsWith("text/event-stream")) {
    throw new Error("The tutor service returned an invalid stream.");
  }
  if (response.body === null) {
    throw new Error("The tutor stream is unavailable in this browser.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed = false;
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const parsed = parseTutorFrames(buffer);
    buffer = parsed.remainder;
    for (const event of parsed.events) {
      onEvent(event);
      if (event.event === "done") {
        completed = true;
      }
    }
    if (done) {
      break;
    }
  }
  if (buffer.trim() !== "") {
    const parsed = parseTutorFrames(`${buffer}\n\n`);
    for (const event of parsed.events) {
      onEvent(event);
      if (event.event === "done") {
        completed = true;
      }
    }
  }
  if (!completed) {
    throw new Error("The tutor response ended before completion.");
  }
}

function appendAssistantDelta(
  delta: string,
  setMessages: (updater: (current: readonly TutorMessage[]) => readonly TutorMessage[]) => void
): void {
  setMessages((current) => {
    const last = current.at(-1);
    if (last?.role !== "assistant") {
      return current;
    }
    return [...current.slice(0, -1), { ...last, content: `${last.content}${delta}` }];
  });
}
