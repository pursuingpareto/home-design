/**
 * Typed API client (openapi-fetch over the generated paths; UI-001 §8, item 2). Every error becomes an
 * ApiError carrying the interfaces.md §7 envelope, so callers branch on stable codes only.
 */

import createClient from "openapi-fetch";

import type { paths } from "./schema";
import type {
  ArtifactType,
  Command,
  CommitResponse,
  ErrorBody,
  ErrorDetail,
  Manifest,
  PayloadByType,
  PreviewResponse,
  PriceBook,
  PriceBookSet,
  ProjectResponse,
  ProjectSummary,
  RevisionSummary,
  Snapshot,
  StoredPriceBook,
  TypedEnvelope,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ErrorDetail[];
  readonly requestId: string | null;

  constructor(status: number, body: Partial<ErrorBody> | null, fallback: string) {
    super(body?.message ?? fallback);
    this.name = "ApiError";
    this.status = status;
    this.code = body?.code ?? (status === 0 ? "NETWORK" : "INTERNAL");
    this.details = body?.details ?? [];
    this.requestId = body?.request_id ?? null;
  }

  get isNetwork(): boolean {
    return this.status === 0;
  }
}

type Fetch = typeof fetch;

export interface ApiOptions {
  baseUrl?: string;
  token: () => string | null;
  fetch?: Fetch;
}

interface Result<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

async function unwrap<T>(request: Promise<Result<T>>): Promise<{ data: T; status: number }> {
  let result: Result<T>;
  try {
    result = await request;
  } catch (error) {
    throw new ApiError(0, null, error instanceof Error ? error.message : "Network error");
  }
  const { data, error, response } = result;
  if (!response.ok) {
    const body = (error as { error?: Partial<ErrorBody> } | undefined)?.error ?? null;
    throw new ApiError(response.status, { request_id: response.headers.get("x-request-id") ?? undefined, ...body }, response.statusText);
  }
  return { data: data as T, status: response.status };
}

export function createApi(options: ApiOptions) {
  const client = createClient<paths>({ baseUrl: options.baseUrl ?? "", fetch: options.fetch });
  client.use({
    onRequest({ request }) {
      const token = options.token();
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      return request;
    },
  });
  const project = (project_id: string) => ({ params: { path: { project_id } } });

  return {
    async listProjects(): Promise<ProjectSummary[]> {
      return (await unwrap(client.GET("/api/v1/projects"))).data.projects;
    },
    async createProject(commandId: string): Promise<{ body: CommitResponse; status: number }> {
      const { data, status } = await unwrap(
        client.POST("/api/v1/projects", { body: { command_id: commandId, type: "CreateReferenceProject", args: {} } }),
      );
      return { body: data, status };
    },
    async getProject(projectId: string): Promise<ProjectResponse> {
      return (await unwrap(client.GET("/api/v1/projects/{project_id}", project(projectId)))).data;
    },
    async listRevisions(projectId: string): Promise<RevisionSummary[]> {
      return (await unwrap(client.GET("/api/v1/projects/{project_id}/revisions", project(projectId)))).data.revisions;
    },
    async getRevision(projectId: string, revisionId: string): Promise<Snapshot> {
      const request = client.GET("/api/v1/projects/{project_id}/revisions/{revision_id}", {
        params: { path: { project_id: projectId, revision_id: revisionId } },
      });
      return (await unwrap(request)).data;
    },
    async preview(projectId: string, command: Command): Promise<PreviewResponse> {
      return (await unwrap(client.POST("/api/v1/projects/{project_id}/commands/preview", { ...project(projectId), body: command }))).data;
    },
    async commit(projectId: string, command: Command, previewToken: string | null): Promise<{ body: CommitResponse; status: number }> {
      const { data, status } = await unwrap(
        client.POST("/api/v1/projects/{project_id}/commands/commit", {
          ...project(projectId),
          body: { command, preview_token: previewToken },
        }),
      );
      return { body: data, status };
    },
    async manifest(projectId: string, revisionId?: string): Promise<Manifest> {
      const request = client.GET("/api/v1/projects/{project_id}/artifacts", {
        params: { path: { project_id: projectId }, query: revisionId ? { revision_id: revisionId } : {} },
      });
      return (await unwrap(request)).data;
    },
    async artifact<T extends ArtifactType>(projectId: string, type: T, revisionId?: string): Promise<TypedEnvelope<PayloadByType[T]>> {
      const request = client.GET("/api/v1/projects/{project_id}/artifacts/{artifact_type}", {
        params: { path: { project_id: projectId, artifact_type: type }, query: revisionId ? { revision_id: revisionId } : {} },
      });
      return (await unwrap(request)).data as TypedEnvelope<PayloadByType[T]>;
    },
    async getPriceBook(projectId: string): Promise<StoredPriceBook | null> {
      return (await unwrap(client.GET("/api/v1/projects/{project_id}/price-book", project(projectId)))).data.price_book;
    },
    async setPriceBook(projectId: string, book: PriceBook): Promise<PriceBookSet> {
      return (await unwrap(client.PUT("/api/v1/projects/{project_id}/price-book", { ...project(projectId), body: book }))).data;
    },
  };
}

export type Api = ReturnType<typeof createApi>;

/**
 * Commit, retrying in-transit failures with the **same** command (same `command_id`), so an earlier
 * success comes back as `replayed` instead of a duplicate (interfaces.md §4; UI-001 §5, step 4).
 */
export async function commitWithRetry(
  api: Api,
  projectId: string,
  command: Command,
  previewToken: string | null,
  attempts = 3,
): Promise<{ body: CommitResponse; status: number }> {
  for (let attempt = 1; ; attempt++) {
    try {
      return await api.commit(projectId, command, previewToken);
    } catch (error) {
      if (!(error instanceof ApiError) || !error.isNetwork || attempt >= attempts) throw error;
    }
  }
}
