/** The caller's projects, newest first, and project creation (UI-001 §4, §8.1). */

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../api/client";
import type { ProjectSummary } from "../api/types";
import { useApp } from "../app/context";
import { ErrorNotice } from "../app/ErrorNotice";
import { href, navigate } from "../app/routing";
import { newCommandId } from "../workspace/commands";

export function ProjectsPage() {
  const { api, signOut } = useApp();
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [creating, setCreating] = useState(false);

  const fail = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.status === 401) signOut();
      else setError(e);
    },
    [signOut],
  );

  useEffect(() => {
    api.listProjects().then(setProjects, fail);
  }, [api, fail]);

  async function create() {
    setCreating(true);
    setError(null);
    const commandId = newCommandId(); // reused on retry: a repeated creation is replayed, not duplicated
    try {
      let result;
      try {
        result = await api.createProject(commandId);
      } catch (e) {
        if (!(e instanceof ApiError && e.isNetwork)) throw e;
        result = await api.createProject(commandId);
      }
      navigate({ name: "workspace", projectId: result.body.project_id, revisionId: null });
    } catch (e) {
      fail(e);
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="projects">
      <h1>Projects</h1>
      <button type="button" onClick={create} disabled={creating}>
        Create Reference House 001
      </button>
      <ErrorNotice error={error} />
      {projects === null ? (
        <p>Loading…</p>
      ) : projects.length === 0 ? (
        <p>No projects yet.</p>
      ) : (
        <table>
          <caption>Your projects, newest first</caption>
          <thead>
            <tr>
              <th scope="col">Project</th>
              <th scope="col">Created</th>
              <th scope="col">Revisions</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.project_id}>
                <td>
                  <a href={href({ name: "workspace", projectId: p.project_id, revisionId: null })}>Reference House 001 · {p.project_id.slice(0, 8)}</a>
                </td>
                <td>{new Date(p.created_at).toLocaleString()}</td>
                <td>{p.head_sequence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
