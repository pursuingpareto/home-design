// Generated from docs/architecture/schemas/connection-catalog.json by scripts/generate-api.mjs. Do not edit by hand.
// The D054 connection catalog, exported from backend/src/homedesign/model/connections.py (D062, UI-003 §10).
// It only limits what the editor offers; the server validates every command (D028).

import type { components } from "./schema";

type JunctionClass = components["schemas"]["ConnectionTypeArgs"]["junction_class"];
type ConnectionType = components["schemas"]["ConnectionTypeArgs"]["connection_type"];

export interface ConnectionCatalogExport {
  catalog_version: string;
  junction_classes: readonly { junction_class: JunctionClass; default: ConnectionType; alternative: ConnectionType }[];
  connection_types: readonly { connection_type: ConnectionType; family: "traditional" | "engineered"; description: string }[];
}

export const CONNECTION_CATALOG: ConnectionCatalogExport = {
  "catalog_version": "vs02-connections-1",
  "connection_types": [
    {
      "connection_type": "PEGGED_MORTISE_TENON",
      "description": "Pegged mortise and tenon. Representational only: no capacity, sizes, or fasteners.",
      "family": "traditional"
    },
    {
      "connection_type": "BRIDLE",
      "description": "Bridle joint. Representational only: no capacity, sizes, or fasteners.",
      "family": "traditional"
    },
    {
      "connection_type": "HOUSED_DOVETAIL",
      "description": "Housed dovetail. Representational only: no capacity, sizes, or fasteners.",
      "family": "traditional"
    },
    {
      "connection_type": "STEEL_KNIFE_PLATE",
      "description": "Concealed steel knife plate with dowels. Representational only: no capacity, sizes, or fasteners.",
      "family": "engineered"
    },
    {
      "connection_type": "JOIST_HANGER",
      "description": "Joist hanger. Representational only: no capacity, sizes, or fasteners.",
      "family": "engineered"
    }
  ],
  "junction_classes": [
    {
      "alternative": "STEEL_KNIFE_PLATE",
      "default": "PEGGED_MORTISE_TENON",
      "junction_class": "post-beam"
    },
    {
      "alternative": "STEEL_KNIFE_PLATE",
      "default": "PEGGED_MORTISE_TENON",
      "junction_class": "post-sill"
    },
    {
      "alternative": "STEEL_KNIFE_PLATE",
      "default": "PEGGED_MORTISE_TENON",
      "junction_class": "brace"
    },
    {
      "alternative": "JOIST_HANGER",
      "default": "HOUSED_DOVETAIL",
      "junction_class": "joist-beam"
    },
    {
      "alternative": "STEEL_KNIFE_PLATE",
      "default": "BRIDLE",
      "junction_class": "rafter-peak"
    },
    {
      "alternative": "STEEL_KNIFE_PLATE",
      "default": "PEGGED_MORTISE_TENON",
      "junction_class": "rafter-foot"
    },
    {
      "alternative": "STEEL_KNIFE_PLATE",
      "default": "PEGGED_MORTISE_TENON",
      "junction_class": "purlin-rafter"
    }
  ]
};
