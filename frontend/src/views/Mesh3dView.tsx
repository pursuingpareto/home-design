/**
 * 3D view of a `mesh3d` payload (UI-001 §4, §6). Plain Three.js behind this component boundary: it
 * takes a payload and a selection and reports picks, and never reads the API or the model.
 * The camera's up vector is +Z, so the data is drawn as served (D026).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import type { Mesh3dPayload } from "../api/types";
import { formatLength, type UnitSystem } from "../units/length";
import { buildMeshScene, highlight, type MeshScene } from "./meshScene";

export interface Mesh3dViewProps {
  mesh: Mesh3dPayload;
  units: UnitSystem;
  selected: string | null;
  onSelect: (memberId: string | null) => void;
}

function footprintExtent(mesh: Mesh3dPayload): { width: number; depth: number } {
  const xs = mesh.envelope.footprint_ring_m.map((p) => p[0] ?? 0);
  const ys = mesh.envelope.footprint_ring_m.map((p) => p[1] ?? 0);
  return { width: Math.max(...xs) - Math.min(...xs), depth: Math.max(...ys) - Math.min(...ys) };
}

export function Mesh3dView({ mesh, units, selected, onSelect }: Mesh3dViewProps) {
  const host = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<MeshScene | null>(null);
  const renderRef = useRef<(() => void) | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const [webgl, setWebgl] = useState(true);
  const extent = useMemo(() => footprintExtent(mesh), [mesh]);

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
    const onUp = (e: PointerEvent) => {
      if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) return; // a drag, not a click
      const rect = renderer.domElement.getBoundingClientRect();
      const ndc = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      raycaster.setFromCamera(ndc, camera);
      const hit = raycaster.intersectObjects([...built.members.values()], false)[0];
      onSelectRef.current((hit?.object.userData.memberId as string | undefined) ?? null);
    };
    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);

    return () => {
      observer.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener("pointerdown", onDown);
      renderer.domElement.removeEventListener("pointerup", onUp);
      built.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      sceneRef.current = null;
      renderRef.current = null;
    };
  }, [mesh]);

  useEffect(() => {
    if (sceneRef.current) {
      highlight(sceneRef.current, selected);
      renderRef.current?.();
    }
  }, [selected, mesh]);

  const summary = `3D frame: ${mesh.members.length} members, footprint ${formatLength(extent.width, units)} × ${formatLength(extent.depth, units)}.`;
  return (
    <figure className="mesh3d" aria-label={summary} data-member-count={mesh.members.length} data-footprint-width-m={extent.width} data-footprint-depth-m={extent.depth}>
      <div ref={host} className="mesh3d-canvas" />
      {!webgl && <p className="notice">3D rendering is not available in this browser.</p>}
      <figcaption>{summary} Drag to orbit, scroll to zoom, click a member to select it.</figcaption>
    </figure>
  );
}
