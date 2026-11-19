import "@testing-library/jest-dom/vitest";

// jsdom has no WebGL. Report "no context" quietly, so Mesh3dView shows its fallback text.
HTMLCanvasElement.prototype.getContext = (() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext;
