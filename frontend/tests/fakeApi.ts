/** An in-memory HTTP fake serving the captured fixtures through the real client (createApi + openapi-fetch). */

import { createApi } from "../src/api/client";
import { fixture } from "./fixtures";

export interface Call {
  method: string;
  path: string;
  body: unknown;
}

type Handler = (call: Call) => { status: number; body: unknown } | undefined;

export function fakeApi(override?: Handler) {
  const calls: Call[] = [];
  const pid = fixture.project.project_id;
  const base = `/api/v1/projects/${pid}`;
  const fetchImpl = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const url = new URL(request.url);
    const text = request.method === "GET" ? "" : await request.text();
    const call = { method: request.method, path: url.pathname + url.search, body: text ? JSON.parse(text) : null };
    calls.push(call);
    const custom = override?.(call);
    const reply = custom ?? route(call);
    return new Response(JSON.stringify(reply.body), {
      status: reply.status,
      headers: { "content-type": "application/json", "x-request-id": "11111111-2222-4333-8444-555555555555" },
    });
  };

  function route({ method, path }: Call): { status: number; body: unknown } {
    const p = path.split("?")[0];
    if (method === "GET" && p === "/api/v1/projects") return { status: 200, body: { projects: [fixture.project] } };
    if (method === "GET" && p === base) return { status: 200, body: fixture.project };
    if (method === "GET" && p === `${base}/revisions`) return { status: 200, body: { revisions: fixture.revisions } };
    if (method === "GET" && p?.startsWith(`${base}/revisions/`)) return { status: 200, body: fixture.snapshot };
    if (method === "GET" && p === `${base}/artifacts`) return { status: 200, body: fixture.manifest };
    const artifact = p?.match(/\/artifacts\/(\w+)$/)?.[1] as keyof typeof fixture.envelopes | undefined;
    if (method === "GET" && artifact && fixture.envelopes[artifact]) return { status: 200, body: fixture.envelopes[artifact] };
    if (method === "GET" && p === `${base}/price-book`) return { status: 200, body: { price_book: null } };
    if (method === "POST" && p === `${base}/commands/preview`) return { status: 200, body: fixture.width_preview };
    return { status: 404, body: { error: { code: "NOT_FOUND", message: "Not found.", details: [], request_id: "x" } } };
  }

  const api = createApi({ baseUrl: "http://api.test", token: () => "test-token", fetch: fetchImpl as typeof fetch });
  return { api, calls };
}
