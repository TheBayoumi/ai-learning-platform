export type TutorStreamEvent =
  | Readonly<{
      event: "meta";
      data: Readonly<{
        model: string;
        prompt_version: string;
        authoritative: false;
      }>;
    }>
  | Readonly<{ event: "delta"; data: Readonly<{ text: string }> }>
  | Readonly<{ event: "done"; data: Readonly<{ status: "complete" }> }>
  | Readonly<{
      event: "error";
      data: Readonly<{ code: string; message: string }>;
    }>;

interface ParsedFrames {
  readonly events: readonly TutorStreamEvent[];
  readonly remainder: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseTutorFrames(buffer: string): ParsedFrames {
  const normalized = buffer.replaceAll("\r\n", "\n");
  const frames = normalized.split("\n\n");
  const remainder = frames.pop() ?? "";
  return {
    events: frames.filter((frame) => frame.trim() !== "").map(parseFrame),
    remainder
  };
}

function parseFrame(frame: string): TutorStreamEvent {
  let eventName = "";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }
  if (eventName === "" || dataLines.length === 0) {
    throw new Error("The tutor stream returned an invalid event.");
  }

  let data: unknown;
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch {
    throw new Error("The tutor stream returned invalid JSON.");
  }
  if (!isRecord(data)) {
    throw new Error("The tutor stream returned an invalid payload.");
  }

  if (
    eventName === "meta" &&
    typeof data.model === "string" &&
    typeof data.prompt_version === "string" &&
    data.authoritative === false
  ) {
    return {
      event: "meta",
      data: {
        model: data.model,
        prompt_version: data.prompt_version,
        authoritative: false
      }
    };
  }
  if (eventName === "delta" && typeof data.text === "string" && data.text !== "") {
    return { event: "delta", data: { text: data.text } };
  }
  if (eventName === "done" && data.status === "complete") {
    return { event: "done", data: { status: "complete" } };
  }
  if (
    eventName === "error" &&
    typeof data.code === "string" &&
    typeof data.message === "string"
  ) {
    return { event: "error", data: { code: data.code, message: data.message } };
  }
  throw new Error("The tutor stream returned an unsupported event.");
}
