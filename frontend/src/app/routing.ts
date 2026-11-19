/** Hash routes: #/sign-in, #/projects, #/projects/<id>, #/projects/<id>/revisions/<rev>. */

import { useEffect, useState } from "react";

export type Route =
  | { name: "sign-in" }
  | { name: "projects" }
  | { name: "workspace"; projectId: string; revisionId: string | null };

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] === "projects" && parts[1]) {
    return { name: "workspace", projectId: parts[1], revisionId: parts[2] === "revisions" && parts[3] ? parts[3] : null };
  }
  if (parts[0] === "sign-in") return { name: "sign-in" };
  return { name: "projects" };
}

export function href(route: Route): string {
  switch (route.name) {
    case "sign-in":
      return "#/sign-in";
    case "projects":
      return "#/projects";
    case "workspace":
      return `#/projects/${encodeURIComponent(route.projectId)}${route.revisionId ? `/revisions/${encodeURIComponent(route.revisionId)}` : ""}`;
  }
}

export function navigate(route: Route): void {
  window.location.hash = href(route);
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
