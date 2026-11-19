/** The project workspace (UI-001 §4): one revision's views, schedule, estimate, edits, and history. */

import { useCallback, useState } from "react";

import { ApiError } from "../api/client";
import type { EstimatePayload } from "../api/types";
import { useApp } from "../app/context";
import { ErrorNotice } from "../app/ErrorNotice";
import { href, navigate } from "../app/routing";
import { undoCommand } from "./commands";
import { EditPanel } from "./EditPanel";
import { ImpactDialog } from "./ImpactDialog";
import { EstimatePanel, HistoryPanel, PreliminaryBanner, RevisionBar, SchedulePanel, ViewsPanel } from "./panels";
import { PriceBookForm } from "./PriceBookForm";
import { useCommandFlow } from "./useCommandFlow";
import { useRevisionData } from "./useRevisionData";

export function Workspace({ projectId, revisionId }: { projectId: string; revisionId: string | null }) {
  const { api, units, signOut } = useApp();
  const [selected, setSelected] = useState<string | null>(null);
  // The line items the price-book form was opened with; kept while the estimate is re-read after a save.
  const [priceItems, setPriceItems] = useState<EstimatePayload | null>(null);
  const [notFound, setNotFound] = useState(false);

  const onError = useCallback(
    (error: unknown) => {
      if (error instanceof ApiError && error.status === 401) signOut();
      if (error instanceof ApiError && error.status === 404 && error.code === "NOT_FOUND") setNotFound(true);
    },
    [signOut],
  );
  const { data, reload, reloadEstimate } = useRevisionData(api, projectId, revisionId, onError);

  const flow = useCommandFlow({
    api,
    projectId,
    onCommitted: () => {
      setSelected(null);
      if (revisionId) navigate({ name: "workspace", projectId, revisionId: null });
      else void reload();
    },
    onConflict: () => void reload(),
    onUnauthorized: signOut,
  });

  if (notFound) {
    return (
      <main className="workspace">
        <p role="alert">Project not found. It may not exist, or it may belong to someone else.</p>
        <a href={href({ name: "projects" })}>Back to projects</a>
      </main>
    );
  }

  const head = data.project?.head_revision_id ?? null;
  const undoTo = (target: string) => head && flow.preview(undoCommand(projectId, head, target));

  return (
    <main className="workspace">
      <nav>
        <a href={href({ name: "projects" })}>Projects</a> / Reference House 001 · <code>{projectId.slice(0, 8)}</code>
      </nav>
      <PreliminaryBanner envelopes={[data.plan, data.mesh, data.schedule, data.estimate]} />
      <RevisionBar data={data} />
      {!data.isHead && data.revisionId && (
        <p className="notice" data-testid="historical-notice">
          You are viewing a historical revision. It is read-only. <a href={href({ name: "workspace", projectId, revisionId: null })}>Go to the head</a>
        </p>
      )}
      <ErrorNotice error={data.error instanceof ApiError && data.error.status === 404 ? null : data.error} />
      <div className="workspace-grid">
        <ViewsPanel data={data} units={units} selected={selected} onSelect={setSelected} />
        <aside className="side">
          {/* Shown for the head route even while reloading, so typed input survives a conflict reload. */}
          {revisionId === null && <EditPanel projectId={projectId} snapshot={data.snapshot} units={units} flow={flow.state} onPreview={(c) => void flow.preview(c)} />}
          <EstimatePanel
            estimate={data.estimate}
            units={units}
            onEditPrices={data.isHead && data.estimate?.payload && !priceItems ? () => setPriceItems(data.estimate?.payload ?? null) : null}
          />
          {priceItems && data.isHead && (
            <PriceBookForm
              api={api}
              projectId={projectId}
              estimate={priceItems}
              units={units}
              onSaved={() => void reloadEstimate()}
              onClose={() => setPriceItems(null)}
            />
          )}
          <HistoryPanel
            revisions={data.revisions}
            shownRevisionId={data.revisionId}
            headRevisionId={head}
            busy={flow.state.step === "previewing" || flow.state.step === "committing"}
            onOpen={(rev) => navigate({ name: "workspace", projectId, revisionId: rev })}
            onUndo={(rev) => void undoTo(rev)}
          />
        </aside>
      </div>
      <SchedulePanel schedule={data.schedule} units={units} selected={selected} onSelect={setSelected} />
      <ImpactDialog state={flow.state} units={units} onConfirm={() => void flow.confirm()} onCancel={flow.cancel} />
    </main>
  );
}
