import { describe, expect, it } from "vitest";

import { parseTutorFrames } from "../lib/tutor-stream";

describe("tutor SSE parser", () => {
  it("parses complete normalized events and preserves an incomplete remainder", () => {
    const parsed = parseTutorFrames(
      'event: meta\r\ndata: {"model":"fake/model","prompt_version":"v1","authoritative":false}\r\n\r\n' +
        'event: delta\ndata: {"text":"First"}\n\n' +
        'event: del'
    );
    expect(parsed.events).toEqual([
      {
        event: "meta",
        data: {
          model: "fake/model",
          prompt_version: "v1",
          authoritative: false
        }
      },
      { event: "delta", data: { text: "First" } }
    ]);
    expect(parsed.remainder).toBe("event: del");
  });

  it("parses terminal and safe error events", () => {
    const parsed = parseTutorFrames(
      'event: done\ndata: {"status":"complete"}\n\n' +
        'event: error\ndata: {"code":"TUTOR_DOWN","message":"Try again."}\n\n'
    );
    expect(parsed.events).toEqual([
      { event: "done", data: { status: "complete" } },
      {
        event: "error",
        data: { code: "TUTOR_DOWN", message: "Try again." }
      }
    ]);
  });

  it.each([
    "event: delta\n\n",
    "data: {}\n\n",
    "event: delta\ndata: not-json\n\n",
    "event: delta\ndata: {}\n\n",
    'event: unknown\ndata: {"value":1}\n\n'
  ])("rejects malformed or unsupported frames: %s", (value) => {
    expect(() => parseTutorFrames(value)).toThrow(/tutor stream/i);
  });
});
