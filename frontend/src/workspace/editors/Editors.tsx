/**
 * The tabbed edit panel (UI-002 §4). Every tab stays mounted, so typed values survive tab switches and
 * conflict reloads; a tab is rebuilt from the stored values after its own command commits.
 */

import { useState, type KeyboardEvent } from "react";

import type { Command } from "../../api/types";
import { ConnectionsEditor } from "./ConnectionsEditor";
import { FootprintEditor } from "./FootprintEditor";
import { FrameEditor } from "./FrameEditor";
import { GridEditor } from "./GridEditor";
import { TAB_LABEL, TAB_OF_COMMAND, type TabId } from "./model";
import { RoofEditor } from "./RoofEditor";
import { SectionsEditor } from "./SectionsEditor";
import type { EditorProps } from "./shared";
import { StoriesEditor } from "./StoriesEditor";

const TABS = Object.keys(TAB_LABEL) as TabId[];

export interface EditorsProps extends EditorProps {
  /** Bumped per tab by the workspace after that tab's command commits. */
  versions: Partial<Record<TabId, number>>;
  onOpenPrices: (() => void) | null;
}

export function tabForCommand(command: Command): TabId | undefined {
  return TAB_OF_COMMAND[command.type];
}

export function Editors(props: EditorsProps) {
  const [active, setActive] = useState<TabId>("footprint");

  function onKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    const next = TABS[(index + step + TABS.length) % TABS.length]!;
    setActive(next);
    document.getElementById(`tab-${next}`)?.focus();
  }

  return (
    <section className="edit-panel" aria-label="Edit">
      <div role="tablist" aria-label="Editors" className="tabs">
        {TABS.map((tab, index) => (
          <button
            key={tab}
            id={`tab-${tab}`}
            type="button"
            role="tab"
            aria-selected={active === tab}
            aria-controls={`panel-${tab}`}
            tabIndex={active === tab ? 0 : -1}
            onClick={() => setActive(tab)}
            onKeyDown={(e) => onKey(e, index)}
          >
            {TAB_LABEL[tab]}
          </button>
        ))}
      </div>
      {TABS.map((tab) => (
        <div key={tab} id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`} hidden={active !== tab}>
          {tab === "footprint" && <FootprintEditor key={props.versions.footprint ?? 0} {...props} />}
          {tab === "stories" && <StoriesEditor key={props.versions.stories ?? 0} {...props} />}
          {tab === "roof" && <RoofEditor key={props.versions.roof ?? 0} {...props} />}
          {tab === "grid" && <GridEditor key={props.versions.grid ?? 0} {...props} />}
          {tab === "frame" && <FrameEditor key={props.versions.frame ?? 0} {...props} />}
          {tab === "sections" && <SectionsEditor key={props.versions.sections ?? 0} {...props} />}
          {tab === "connections" && <ConnectionsEditor key={props.versions.connections ?? 0} {...props} />}
        </div>
      ))}
    </section>
  );
}
