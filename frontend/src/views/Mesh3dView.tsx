/**
 * 3D view of a `mesh3d` payload (UI-001 §4, §6). Plain Three.js behind this component boundary: it
 * takes a payload and the highlighted IDs and reports picks, and never reads the API or the model.
 * The camera's up vector is +Z, so the data is drawn as served (D026). Connection glyphs are drawn
 * over the members and picked before them (D062).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import type { Mesh3dPayload } from "../api/types";
import { roleLabel, type Role } from "../display/labels";
import { formatLength, type UnitSystem } from "../units/length";
import type { Highlight, Pick } from "./highlight";
import { Legend, typesOf } from "./Legend";
import { glyphTitle, groupMarkers } from "./markers";
import { buildMeshScene, highlight, pick, setMarkersVisible, type MeshScene } from "./meshScene";

export interface Mesh3dViewProps {
  mesh: Mesh3dPayload;
  units: UnitSystem;
  highlight: Highlight;
  showConnections: boolean;
  onSelect: (pick: Pick | null) => void;
}

function footprintExtent(mesh: Mesh3dPayload): { width: number; depth: number } {
  const xs = mesh.envelope.footprint_ring_m.map((p) => p[0] ?? 0);
  const ys = mesh.envelope.footprint_ring_m.map((p) => p[1] ?? 0);
  return { width: Math.max(...xs) - Math.min(...xs), depth: Math.max(...ys) - Math.min(...ys) };
}

export function Mesh3dView({ mesh, units, highlight: highlighted, showConnections, onSelect }: Mesh3dViewProps) {
  const host = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<MeshScene | null>(null);
  const renderRef = useRef<(() => void) | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const [webgl, setWebgl] = useState(true);
  const extent = useMemo(() => footprintExtent(mesh), [mesh]);
  const glyphs = useMemo(() => groupMarkers(mesh.connections, (m) => m.location_m), [mesh]);
  const roles = useMemo(() => new Set<Role>(mesh.members.map((m) => m.role)), [mesh]);
  const showRef = useRef(showConnections);
  showRef.current = showConnections;

  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch {
      setWebgl(false);
      return;
    }
    const built = buildMeshScene(mesh);
    setMarkersVisible(built, showRef.current);
    sceneRef.current = built;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf6f7f9);
    scene.add(built.group, new THREE.AmbientLight(0xffffff, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 1.8);
    sun.position.set(-10, -20, 30);
    scene.add(sun);

    const center = built.bounds.getCenter(new THREE.Vector3());
    const size = built.bounds.getSize(new THREE.Vector3()).length();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, size * 20);
    camera.up.set(0, 0, 1);
    camera.position.copy(center).add(new THREE.Vector3(-0.9, -1.3, 0.8).multiplyScalar(size));
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.copy(center);
    controls.update();
    element.appendChild(renderer.domElement);

    const render = () => renderer.render(scene, camera);
    renderRef.current = render;
    const resize = () => {
      const width = element.clientWidth || 600;
      const height = element.clientHeight || 400;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      render();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    controls.addEventListener("change", render);
    resize();

    const raycaster = new THREE.Raycaster();
    let down: { x: number; y: number } | null = null;
    const onDown = (e: PointerEvent) => (down = { x: e.clientX, y: e.clientY });
    const pickAt = (e: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      const ndc = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      raycaster.setFromCamera(ndc, camera);
      return pick(built, raycaster);
    };
    const onUp = (e: PointerEvent) => {
      if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) return; // a drag, not a click
      onSelectRef.current(pickAt(e));
    };
    // The hovered member's or glyph's tooltip, as the plan's titles show them (UI-003 §5.1).
    let hoverFrame = 0;
    const onMove = (e: PointerEvent) => {
      if (e.buttons || hoverFrame) return;
      hoverFrame = requestAnimationFrame(() => {
        hoverFrame = 0;
        const hit = pickAt(e);
        let title = "";
        if (hit?.kind === "member") {
          const box = built.members.get(hit.id);
          title = box ? `${roleLabel(box.userData.role as string)} · ${box.userData.generationKey as string}` : "";
        } else if (hit) {
          const glyph = built.markers.glyphs.find((g) => g.markers[0]?.connection_id === hit.ids[0]);
          title = glyph ? glyphTitle(glyph) : "";
        }
        renderer.domElement.title = title;
      });
    };
    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);
    renderer.domElement.addEventListener("pointermove", onMove);

    return () => {
      observer.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener("pointerdown", onDown);
      renderer.domElement.removeEventListener("pointerup", onUp);
      renderer.domElement.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(hoverFrame);
      built.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      sceneRef.current = null;
      renderRef.current = null;
    };
  }, [mesh]);

  useEffect(() => {
    if (sceneRef.current) {
      highlight(sceneRef.current, highlighted);
      setMarkersVisible(sceneRef.current, showConnections);
      renderRef.current?.();
    }
  }, [highlighted, showConnections, mesh]);

  const summary = `3D frame: ${mesh.members.length} members, ${mesh.connections.length} connections, footprint ${formatLength(extent.width, units)} × ${formatLength(extent.depth, units)}.`;
  return (
    <figure
      className="mesh3d"
      aria-label={summary}
      data-member-count={mesh.members.length}
      data-connection-count={mesh.connections.length}
      data-glyph-count={showConnections ? glyphs.length : 0}
      data-footprint-width-m={extent.width}
      data-footprint-depth-m={extent.depth}
      data-eave-z-m={mesh.envelope.z_eave_m}
    >
      <div ref={host} className="mesh3d-canvas" />
      {!webgl && <p className="notice">3D rendering is not available in this browser.</p>}
      <Legend testId="mesh-legend" roles={roles} types={showConnections ? typesOf(mesh.connections) : []} mixed={showConnections && glyphs.some((g) => g.style === "mixed")} />
      <figcaption>
        {summary} Drag to orbit, scroll to zoom, click a member{showConnections ? " or a connection" : ""} to select it.
      </figcaption>
    </figure>
  );
}
