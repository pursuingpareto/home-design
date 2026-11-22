// Generated from docs/architecture/schemas/openapi.v1.json by scripts/generate-api.mjs. Do not edit by hand.

export interface paths {
    "/api/v1/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** The caller's own projects, newest first (UI-001 §8.1) */
        get: operations["listProjects"];
        put?: never;
        /** Create a reference project (interfaces.md §2, §4) */
        post: operations["createProject"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Project metadata, head, and the caller's permissions */
        get: operations["getProject"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/artifacts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Artifact status manifest (artifacts.md §3); the head when revision_id is omitted */
        get: operations["getArtifactManifest"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/artifacts/{artifact_type}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** One derived artifact (artifacts.md §2); derived on read when missing or stale */
        get: operations["getArtifact"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/commands/commit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Commit a command (interfaces.md §4) */
        post: operations["commitCommand"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/commands/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Preview a command without writing anything (interfaces.md §3) */
        post: operations["previewCommand"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/price-book": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** The current price book, or null */
        get: operations["getPriceBook"];
        /** Set a new price-book version (artifacts.md §8.2) */
        put: operations["setPriceBook"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Revision history, ordered by sequence */
        get: operations["listRevisions"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/revisions/{revision_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** An immutable snapshot, as its RFC 8785 canonical bytes (D029, D030) */
        get: operations["getRevision"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AddOpening */
        AddOpening: {
            args: components["schemas"]["AddOpeningArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "AddOpening";
        };
        /**
         * AddOpeningArgs
         * @description D069: a rough opening in one wall (MODEL-006 §8.2); all required.
         */
        AddOpeningArgs: {
            /** Height M */
            height_m: number;
            /** Offset M */
            offset_m: number;
            /**
             * Opening Kind
             * @enum {string}
             */
            opening_kind: "WINDOW" | "DOOR";
            /** Sill Height M */
            sill_height_m: number;
            /** Wall Id */
            wall_id: string;
            /** Width M */
            width_m: number;
        };
        /** AddSection */
        AddSection: {
            args: components["schemas"]["AddSectionArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "AddSection";
        };
        /** AddSectionArgs */
        AddSectionArgs: {
            /** Actual Depth M */
            actual_depth_m: number;
            /** Actual Width M */
            actual_width_m: number;
            /** Nominal Label */
            nominal_label: string;
        };
        /** AreaWeightedFigure */
        AreaWeightedFigure: {
            /** Missing Inputs */
            missing_inputs: components["schemas"]["MissingInput"][];
            /** Net Area M2 */
            net_area_m2: number;
            /** R Value M2 K W */
            r_value_m2_k_w: number | null;
            /** U Value W M2 K */
            u_value_w_m2_k: number | null;
            /** Ua W K */
            ua_w_k: number | null;
        };
        /**
         * VS-01 artifact envelope (artifacts.md §2)
         * @description Common envelope for every artifact response (artifacts.md §2).
         */
        ArtifactEnvelope: {
            /**
             * Artifact Type
             * @enum {string}
             */
            artifact_type: "plan2d" | "mesh3d" | "timber_schedule" | "assembly_schedule" | "preliminary_estimate";
            /**
             * @default {
             *       "construction_approved": false,
             *       "permit_ready": false,
             *       "structurally_verified": false
             *     }
             */
            claims: components["schemas"]["Claims"];
            error: components["schemas"]["Message"] | null;
            /** Generated At */
            generated_at: string | null;
            /** Generator Id */
            generator_id: string | null;
            /** Generator Version */
            generator_version: string | null;
            /** Head */
            head: boolean;
            /** Input Fingerprint */
            input_fingerprint: string | null;
            /** Payload */
            payload?: {
                [key: string]: unknown;
            } | null;
            /** Project Id */
            project_id: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: 1;
            /** Source Revision Id */
            source_revision_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "MISSING" | "QUEUED" | "COMPUTING" | "CURRENT" | "FAILED" | "STALE" | "UNAVAILABLE" | "SUPERSEDED";
            /**
             * Suitability
             * @default preliminary
             * @constant
             */
            suitability: "preliminary";
            /** Warnings */
            warnings: components["schemas"]["Message"][];
        };
        /**
         * AssemblyDefinition
         * @description A fixed layered wall definition, a catalog record (D067; MODEL-006 §4.3).
         */
        AssemblyDefinition: {
            /**
             * Family
             * @enum {string}
             */
            family: "STRAW_BALE" | "STUD_INFILL";
            /** Id */
            id: string;
            /** Installation Note */
            installation_note: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "AssemblyDefinition";
            /** Label */
            label: string;
            /** Layers */
            layers: components["schemas"]["Layer"][];
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Unverified Climate Details */
            unverified_climate_details: string[];
        };
        /**
         * AssemblyLine
         * @description One line per definition and layer in use, the framing layer's fill included (D070, D082; ART-003 §7.1).
         */
        AssemblyLine: {
            /** Amount Minor */
            amount_minor: number | null;
            /** Assembly Label */
            assembly_label: string;
            /** Key */
            key: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "assembly";
            /** Layer */
            layer: string;
            /**
             * Layer Function
             * @enum {string}
             */
            layer_function: "FINISH" | "SHEATHING" | "INSULATION" | "FRAMING";
            /** Material Name */
            material_name: string;
            /** Priced */
            priced: boolean;
            /**
             * Quantity Unit
             * @constant
             */
            quantity_unit: "m2";
            /** Quantity Value */
            quantity_value: number;
            /** Unit Price Minor */
            unit_price_minor: number | null;
        };
        /**
         * AssemblyOpeningRow
         * @description No position (ART-003 §4.3): positions belong to the views.
         */
        AssemblyOpeningRow: {
            /** Area M2 */
            area_m2: number;
            /** Has Jacks */
            has_jacks: boolean;
            /** Height M */
            height_m: number;
            /** Opening Id */
            opening_id: string;
            /**
             * Opening Kind
             * @enum {string}
             */
            opening_kind: "WINDOW" | "DOOR";
            /** Wall Id */
            wall_id: string;
            /** Wall Key */
            wall_key: string;
            /** Width M */
            width_m: number;
        };
        /** assembly_schedule payload (artifacts.md §7A) */
        AssemblySchedulePayload: {
            /** Assumptions */
            assumptions: components["schemas"]["Assumption"][];
            /** Definition Aggregates */
            definition_aggregates: components["schemas"]["DefinitionAggregate"][];
            /** Definitions */
            definitions: components["schemas"]["DefinitionEntry"][];
            /** Framing Aggregates */
            framing_aggregates: components["schemas"]["FramingAggregate"][];
            /** Layer Aggregates */
            layer_aggregates: components["schemas"]["LayerAggregate"][];
            /** Opening Aggregates */
            opening_aggregates: components["schemas"]["OpeningAggregate"][];
            /** Openings */
            openings: components["schemas"]["AssemblyOpeningRow"][];
            /**
             * Quantity Basis
             * @default reference
             * @constant
             */
            quantity_basis: "reference";
            thermal: components["schemas"]["ThermalFigures"];
            totals: components["schemas"]["AssemblyTotals"];
            /**
             * @default {
             *       "area": "m2",
             *       "count": "1",
             *       "heat_flow": "W/K",
             *       "length": "m",
             *       "thermal_resistance": "m2.K/W",
             *       "thermal_transmittance": "W/(m2.K)",
             *       "volume": "m3"
             *     }
             */
            units: components["schemas"]["AssemblyUnits"];
            /** Wall Framing */
            wall_framing: components["schemas"]["WallFramingRow"][];
            /** Walls */
            walls: components["schemas"]["AssemblyWallRow"][];
        };
        /** AssemblyTotals */
        AssemblyTotals: {
            /** Framing Face Area M2 */
            framing_face_area_m2: number;
            /** Gross Area M2 */
            gross_area_m2: number;
            /** Net Area M2 */
            net_area_m2: number;
            /** Opening Area M2 */
            opening_area_m2: number;
            /** Opening Count */
            opening_count: number;
            /** Wall Count */
            wall_count: number;
        };
        /** AssemblyUnits */
        AssemblyUnits: {
            /**
             * Area
             * @default m2
             * @constant
             */
            area: "m2";
            /**
             * Count
             * @default 1
             * @constant
             */
            count: "1";
            /**
             * Heat Flow
             * @default W/K
             * @constant
             */
            heat_flow: "W/K";
            /**
             * Length
             * @default m
             * @constant
             */
            length: "m";
            /**
             * Thermal Resistance
             * @default m2.K/W
             * @constant
             */
            thermal_resistance: "m2.K/W";
            /**
             * Thermal Transmittance
             * @default W/(m2.K)
             * @constant
             */
            thermal_transmittance: "W/(m2.K)";
            /**
             * Volume
             * @default m3
             * @constant
             */
            volume: "m3";
        };
        /** AssemblyWallRow */
        AssemblyWallRow: {
            /** Assembly Definition Id */
            assembly_definition_id: string;
            /** Assembly Label */
            assembly_label: string;
            /**
             * Elevation Side
             * @enum {string}
             */
            elevation_side: "south" | "north" | "west" | "east";
            /** Framing Face Area M2 */
            framing_face_area_m2: number;
            /** Framing Fraction */
            framing_fraction: number;
            /** Generation Key */
            generation_key: string;
            /** Gross Area M2 */
            gross_area_m2: number;
            /** Height M */
            height_m: number;
            /** Length M */
            length_m: number;
            /** Level Id */
            level_id: string;
            /** Level Index */
            level_index: number;
            /** Net Area M2 */
            net_area_m2: number;
            /** Opening Area M2 */
            opening_area_m2: number;
            /** R Value M2 K W */
            r_value_m2_k_w: number | null;
            /** U Value W M2 K */
            u_value_w_m2_k: number | null;
            /** Ua W K */
            ua_w_k: number | null;
            /** Wall Id */
            wall_id: string;
        };
        /** Assumption */
        Assumption: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /**
         * BuckFraming
         * @description A straw bale framing layer: bucks at openings, no girts in VS-02b (D066, D067).
         */
        BuckFraming: {
            /** Buck Section Id */
            buck_section_id: string;
            /** Framing Material Id */
            framing_material_id: string;
            framing_thermal_conductivity_w_m_k: components["schemas"]["DeclaredValue"] | null;
            /** Girt Count */
            girt_count: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "BUCK";
        };
        /** BuckFramingSummary */
        BuckFramingSummary: {
            /** Buck Section */
            buck_section: string;
            /** Framing Material Id */
            framing_material_id: string;
            /** Framing Material Name */
            framing_material_name: string;
            framing_thermal_conductivity_w_m_k: components["schemas"]["DeclaredValue"] | null;
            /** Girt Count */
            girt_count: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "BUCK";
        };
        /** Building */
        Building: {
            /** Footprint Id */
            footprint_id: string;
            /** Frame System Id */
            frame_system_id: string;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "Building";
            /** Level Ids */
            level_ids: string[];
            /** Name */
            name: string;
            /** Roof Id */
            roof_id: string;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 2;
            /** Wall System Id */
            wall_system_id: string;
        };
        /** CatalogType */
        CatalogType: {
            /**
             * Connection Type
             * @enum {string}
             */
            connection_type: "PEGGED_MORTISE_TENON" | "BRIDLE" | "HOUSED_DOVETAIL" | "STEEL_KNIFE_PLATE" | "JOIST_HANGER";
            /** Description */
            description: string;
            /**
             * Family
             * @enum {string}
             */
            family: "traditional" | "engineered";
        };
        /** Claims */
        Claims: {
            /**
             * Construction Approved
             * @default false
             * @constant
             */
            construction_approved: false;
            /**
             * Permit Ready
             * @default false
             * @constant
             */
            permit_ready: false;
            /**
             * Structurally Verified
             * @default false
             * @constant
             */
            structurally_verified: false;
        };
        /**
         * Command
         * @description Any VS-01 command envelope, discriminated by `type` (interfaces.md §2).
         */
        Command: components["schemas"]["CreateReferenceProject"] | components["schemas"]["SetFootprintDimensions"] | components["schemas"]["SetStoryHeights"] | components["schemas"]["SetGableRoofParameters"] | components["schemas"]["SetTimberGrid"] | components["schemas"]["SetMemberSection"] | components["schemas"]["SetFrameParameters"] | components["schemas"]["SetConnectionType"] | components["schemas"]["AddSection"] | components["schemas"]["UndoToRevision"] | components["schemas"]["SetWallAssembly"] | components["schemas"]["AddOpening"] | components["schemas"]["SetOpening"] | components["schemas"]["RemoveOpening"];
        /** CommitRequest */
        CommitRequest: {
            /** Command */
            command: components["schemas"]["CreateReferenceProject"] | components["schemas"]["SetFootprintDimensions"] | components["schemas"]["SetStoryHeights"] | components["schemas"]["SetGableRoofParameters"] | components["schemas"]["SetTimberGrid"] | components["schemas"]["SetMemberSection"] | components["schemas"]["SetFrameParameters"] | components["schemas"]["SetConnectionType"] | components["schemas"]["AddSection"] | components["schemas"]["UndoToRevision"] | components["schemas"]["SetWallAssembly"] | components["schemas"]["AddOpening"] | components["schemas"]["SetOpening"] | components["schemas"]["RemoveOpening"];
            /**
             * Preview Token
             * @description Required for consequential commands that are not no-ops (D047).
             * @default null
             */
            preview_token: string | null;
        };
        /** CommitResponse */
        CommitResponse: {
            /** Artifact Statuses */
            artifact_statuses: {
                [key: string]: "CURRENT" | "STALE" | "MISSING" | "UNAVAILABLE" | "FAILED";
            };
            /** Is Noop */
            is_noop: boolean;
            /** Operation Id */
            operation_id: string;
            /** Parent Revision Id */
            parent_revision_id: string | null;
            /** Project Id */
            project_id: string;
            /**
             * Replayed
             * @description Present (true) only for an idempotent retry.
             */
            replayed?: true | null;
            /** Revision Id */
            revision_id: string;
            /** Sequence */
            sequence: number;
        };
        /**
         * Connection
         * @description A generated junction of exactly two members (D054, MODEL-005 §4.4). Makes no capacity claim.
         */
        Connection: {
            /**
             * Connection Type
             * @enum {string}
             */
            connection_type: "PEGGED_MORTISE_TENON" | "BRIDLE" | "HOUSED_DOVETAIL" | "STEEL_KNIFE_PLATE" | "JOIST_HANGER";
            /** Generation Key */
            generation_key: string;
            /** Id */
            id: string;
            /**
             * Junction Class
             * @enum {string}
             */
            junction_class: "post-beam" | "post-sill" | "brace" | "joist-beam" | "rafter-peak" | "rafter-foot" | "purlin-rafter";
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "Connection";
            /** Location M */
            location_m: number[];
            /** Member Ids */
            member_ids: string[];
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
        };
        /** ConnectionAggregate */
        ConnectionAggregate: {
            /**
             * Connection Type
             * @enum {string}
             */
            connection_type: "PEGGED_MORTISE_TENON" | "BRIDLE" | "HOUSED_DOVETAIL" | "STEEL_KNIFE_PLATE" | "JOIST_HANGER";
            /** Count */
            count: number;
            /**
             * Junction Class
             * @enum {string}
             */
            junction_class: "post-beam" | "post-sill" | "brace" | "joist-beam" | "rafter-peak" | "rafter-foot" | "purlin-rafter";
        };
        /** ConnectionCatalog */
        ConnectionCatalog: {
            /**
             * Catalog Version
             * @constant
             */
            catalog_version: "vs02-connections-1";
            /** Types */
            types: components["schemas"]["CatalogType"][];
        };
        /**
         * ConnectionChanges
         * @description Generated connections the commit adds, removes, or changes (CONN-001 §7.2), shaped like `members`.
         */
        ConnectionChanges: {
            /** Added */
            added: components["schemas"]["ConnectionRef"][];
            /** Removed */
            removed: components["schemas"]["ConnectionRef"][];
            /** Updated */
            updated: string[];
        };
        /** ConnectionLine */
        ConnectionLine: {
            /** Amount Minor */
            amount_minor: number | null;
            /**
             * Connection Type
             * @enum {string}
             */
            connection_type: "PEGGED_MORTISE_TENON" | "BRIDLE" | "HOUSED_DOVETAIL" | "STEEL_KNIFE_PLATE" | "JOIST_HANGER";
            /** Key */
            key: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "connection";
            /** Priced */
            priced: boolean;
            /**
             * Quantity Unit
             * @constant
             */
            quantity_unit: "each";
            /** Quantity Value */
            quantity_value: number;
            /** Unit Price Minor */
            unit_price_minor: number | null;
        };
        /** ConnectionRef */
        ConnectionRef: {
            /** Generation Key */
            generation_key: string;
            /** Id */
            id: string;
        };
        /**
         * ConnectionTypeArgs
         * @description D054, D059: a type per junction class, never per connection (CONN-001 §8.1).
         */
        ConnectionTypeArgs: {
            /**
             * Connection Type
             * @enum {string}
             */
            connection_type: "PEGGED_MORTISE_TENON" | "BRIDLE" | "HOUSED_DOVETAIL" | "STEEL_KNIFE_PLATE" | "JOIST_HANGER";
            /**
             * Junction Class
             * @enum {string}
             */
            junction_class: "post-beam" | "post-sill" | "brace" | "joist-beam" | "rafter-peak" | "rafter-foot" | "purlin-rafter";
        };
        /**
         * CreateProjectRequest
         * @description The creation envelope (interfaces.md §2): `CreateReferenceProject` without project or base revision.
         */
        CreateProjectRequest: components["schemas"]["CreateReferenceProject"];
        /**
         * CreateReferenceProject
         * @description Creation envelope: no project or base revision exists yet (interfaces.md §2).
         */
        CreateReferenceProject: {
            args: components["schemas"]["NoArgs"];
            /** Command Id */
            command_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "CreateReferenceProject";
        };
        /**
         * DeclaredValue
         * @description A declared property value with its provenance (D071, D075). The unit is fixed by the field name, in SI.
         */
        DeclaredValue: {
            /** Date */
            date: string;
            /** Note */
            note: string | null;
            /** Source */
            source: string;
            /** Value */
            value: number;
        };
        /** DefinitionAggregate */
        DefinitionAggregate: {
            /** Assembly Label */
            assembly_label: string;
            /** Gross Area M2 */
            gross_area_m2: number;
            /** Net Area M2 */
            net_area_m2: number;
            /** Opening Area M2 */
            opening_area_m2: number;
            /** Opening Count */
            opening_count: number;
            /** Wall Count */
            wall_count: number;
        };
        /** DefinitionEntry */
        DefinitionEntry: {
            /** Assembly Definition Id */
            assembly_definition_id: string;
            /**
             * Family
             * @enum {string}
             */
            family: "STRAW_BALE" | "STUD_INFILL";
            /** Installation Note */
            installation_note: string;
            /** Label */
            label: string;
            /** Layers */
            layers: components["schemas"]["DefinitionLayer"][];
            /** Total Thickness M */
            total_thickness_m: number;
            /** Unverified Climate Details */
            unverified_climate_details: string[];
        };
        /**
         * DefinitionLayer
         * @description A layer as stored, with its material's name and, for the framing layer, its framing by section label.
         */
        DefinitionLayer: {
            /** Framing */
            framing: (components["schemas"]["StudFramingSummary"] | components["schemas"]["BuckFramingSummary"]) | null;
            /**
             * Function
             * @enum {string}
             */
            function: "FINISH" | "SHEATHING" | "INSULATION" | "FRAMING";
            /** Material Id */
            material_id: string;
            /** Material Name */
            material_name: string;
            /** Name */
            name: string;
            thermal_conductivity_w_m_k: components["schemas"]["DeclaredValue"] | null;
            thermal_resistance_m2_k_w: components["schemas"]["DeclaredValue"] | null;
            /** Thickness M */
            thickness_m: number;
            vapor_permeance_kg_pa_s_m2: components["schemas"]["DeclaredValue"] | null;
        };
        /** Dimension */
        Dimension: {
            /** End M */
            end_m: number[];
            /**
             * Id
             * @enum {string}
             */
            id: "footprint-width" | "footprint-depth";
            /** Start M */
            start_m: number[];
            /** Value M */
            value_m: number;
        };
        /** Envelope3d */
        Envelope3d: {
            /** Footprint Ring M */
            footprint_ring_m: number[][];
            /** Level Z M */
            level_z_m: number[];
            roof: components["schemas"]["GableRoofGeometry"];
            /** Z Eave M */
            z_eave_m: number;
        };
        /** ErrorBody */
        ErrorBody: {
            /** Code */
            code: string;
            /** Details */
            details: components["schemas"]["ErrorDetail"][];
            /**
             * Message
             * @description Human-readable; not part of the contract.
             */
            message: string;
            /** Request Id */
            request_id: string;
        };
        /** ErrorDetail */
        ErrorDetail: {
            /**
             * Code
             * @description Detail code from building-model.md §6.1.
             */
            code: string;
            /**
             * Path
             * @description D036 path from the root of the validated document.
             */
            path: string;
            /**
             * Related Paths
             * @description D037; omitted when empty.
             */
            related_paths?: string[] | null;
            /** Value */
            value?: unknown;
        };
        /** ErrorEnvelope */
        ErrorEnvelope: {
            error: components["schemas"]["ErrorBody"];
        };
        /** FieldChange */
        FieldChange: {
            /** After */
            after: unknown;
            /** Before */
            before: unknown;
            /** Entity Id */
            entity_id: string;
            /** Entity Kind */
            entity_kind: string;
            /** Field */
            field: string;
        };
        /** Footprint */
        Footprint: {
            /** Depth M */
            depth_m: number;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "Footprint";
            /** Origin M */
            origin_m: number[];
            /** Rotation Rad */
            rotation_rad: number;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Width M */
            width_m: number;
        };
        /** FootprintArgs */
        FootprintArgs: {
            /** Depth M */
            depth_m: number;
            /** Width M */
            width_m: number;
        };
        /**
         * FrameParameters
         * @description Inputs to the frame's generation rule (MODEL-005 §5). Bounds are checked in stages 3 and 4.
         */
        FrameParameters: {
            /** Joist Spacing M */
            joist_spacing_m: number;
            /** Knee Brace Leg M */
            knee_brace_leg_m: number;
            /** Knee Braces Eave */
            knee_braces_eave: boolean;
            /** Knee Braces Level 1 */
            knee_braces_level_1: boolean;
            /** Purlins Per Slope */
            purlins_per_slope: number;
        };
        /**
         * FrameParametersArgs
         * @description D057: every frame parameter, all required (MODEL-005 §7.1).
         */
        FrameParametersArgs: {
            /** Joist Spacing M */
            joist_spacing_m: number;
            /** Knee Brace Leg M */
            knee_brace_leg_m: number;
            /** Knee Braces Eave */
            knee_braces_eave: boolean;
            /** Knee Braces Level 1 */
            knee_braces_level_1: boolean;
            /** Purlins Per Slope */
            purlins_per_slope: number;
        };
        /** FrameSystem */
        FrameSystem: {
            /** Connection Defaults */
            connection_defaults: {
                [key: string]: "PEGGED_MORTISE_TENON" | "BRIDLE" | "HOUSED_DOVETAIL" | "STEEL_KNIFE_PLATE" | "JOIST_HANGER";
            };
            /** Connection Ids */
            connection_ids: string[];
            /** Generation Mode */
            generation_mode: string;
            /** Grid Id */
            grid_id: string;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "FrameSystem";
            /** Member Defaults */
            member_defaults: {
                [key: string]: components["schemas"]["RoleDefault"];
            };
            /** Member Ids */
            member_ids: string[];
            parameters: components["schemas"]["FrameParameters"];
            /**
             * Schema Version
             * @constant
             */
            schema_version: 2;
        };
        /** FramingAggregate */
        FramingAggregate: {
            /** Count */
            count: number;
            /** Nominal Section */
            nominal_section: string;
            /**
             * Piece Kind
             * @enum {string}
             */
            piece_kind: "STUD" | "GIRT" | "KING" | "JACK" | "HEADER" | "ROUGH_SILL" | "CRIPPLE" | "BUCK_JAMB" | "BUCK_HEAD" | "BUCK_SILL";
            /** Total Length M */
            total_length_m: number;
        };
        /** GableRoof */
        GableRoof: {
            /** Eave Overhang M */
            eave_overhang_m: number;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "GableRoof";
            /** Pitch Rad */
            pitch_rad: number;
            /**
             * Ridge Axis
             * @enum {string}
             */
            ridge_axis: "X" | "Y";
            /** Ridge Offset M */
            ridge_offset_m: number;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
        };
        /** GableRoofArgs */
        GableRoofArgs: {
            /** Eave Overhang M */
            eave_overhang_m: number;
            /** Pitch Rad */
            pitch_rad: number;
        };
        /** GableRoofGeometry */
        GableRoofGeometry: {
            /**
             * Kind
             * @default gable
             * @constant
             */
            kind: "gable";
            /** Pitch Rad */
            pitch_rad: number;
            /**
             * Ridge Axis
             * @constant
             */
            ridge_axis: "X";
            /** Ridge End M */
            ridge_end_m: number[];
            /** Ridge Start M */
            ridge_start_m: number[];
            /** Surfaces */
            surfaces: components["schemas"]["RoofSurface"][];
        };
        /**
         * GridLineArg
         * @description Either ``{"id", "fraction"}`` (keep an existing line) or ``{"fraction"}`` (new line).
         */
        GridLineArg: {
            /** Fraction */
            fraction: number;
            /** Id */
            id?: string;
        };
        /**
         * Layer
         * @description One layer of an assembly definition, embedded in it (D074). Only the FRAMING layer has ``framing``.
         */
        Layer: {
            /** Framing */
            framing: (components["schemas"]["StudFraming"] | components["schemas"]["BuckFraming"]) | null;
            /**
             * Function
             * @enum {string}
             */
            function: "FINISH" | "SHEATHING" | "INSULATION" | "FRAMING";
            /** Material Id */
            material_id: string;
            /** Name */
            name: string;
            thermal_conductivity_w_m_k: components["schemas"]["DeclaredValue"] | null;
            thermal_resistance_m2_k_w: components["schemas"]["DeclaredValue"] | null;
            /** Thickness M */
            thickness_m: number;
            vapor_permeance_kg_pa_s_m2: components["schemas"]["DeclaredValue"] | null;
        };
        /** LayerAggregate */
        LayerAggregate: {
            /** Area M2 */
            area_m2: number;
            /** Assembly Label */
            assembly_label: string;
            /**
             * Function
             * @enum {string}
             */
            function: "FINISH" | "SHEATHING" | "INSULATION" | "FRAMING";
            /** Layer */
            layer: string;
            /** Material Name */
            material_name: string;
            /** Thickness M */
            thickness_m: number;
            /** Volume M3 */
            volume_m3: number;
        };
        /** Level */
        Level: {
            /** Elevation M */
            elevation_m: number;
            /** Id */
            id: string;
            /** Index */
            index: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "Level";
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Story Height M */
            story_height_m: number;
        };
        /** Manifest */
        Manifest: {
            /** Artifacts */
            artifacts: components["schemas"]["ManifestEntry"][];
            /** Head */
            head: boolean;
            /** Project Id */
            project_id: string;
            /** Revision Id */
            revision_id: string;
        };
        /** ManifestEntry */
        ManifestEntry: {
            /** Artifact Type */
            artifact_type: string;
            /** Generator Version */
            generator_version: string | null;
            /** Input Fingerprint */
            input_fingerprint: string | null;
            /** Source Revision Id */
            source_revision_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "MISSING" | "QUEUED" | "COMPUTING" | "CURRENT" | "FAILED" | "STALE" | "UNAVAILABLE" | "SUPERSEDED";
        };
        /** Material */
        Material: {
            /** Density Kg M3 */
            density_kg_m3: number | null;
            /** Grade */
            grade: string | null;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "Material";
            /** Name */
            name: string;
            /** Provenance */
            provenance: string | null;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Species */
            species: string | null;
        };
        /** MemberChanges */
        MemberChanges: {
            /** Added */
            added: components["schemas"]["MemberRef"][];
            /** Removed */
            removed: components["schemas"]["MemberRef"][];
            /** Updated */
            updated: string[];
        };
        /** MemberRef */
        MemberRef: {
            /** Generation Key */
            generation_key: string;
            /** Id */
            id: string;
        };
        /** MemberSectionArgs */
        MemberSectionArgs: {
            /**
             * Role
             * @enum {string}
             */
            role: "POST" | "BEAM" | "SILL" | "FLOOR_JOIST" | "PRINCIPAL_RAFTER" | "PURLIN" | "KNEE_BRACE";
            /** Section Id */
            section_id: string;
        };
        /** mesh3d payload (artifacts.md §6) */
        Mesh3dPayload: {
            /** Connections */
            connections: components["schemas"]["MeshConnection"][];
            envelope: components["schemas"]["Envelope3d"];
            /** Members */
            members: components["schemas"]["MeshMember"][];
            /**
             * Units
             * @default m
             * @constant
             */
            units: "m";
            /** Wall Framing */
            wall_framing: components["schemas"]["MeshWallFramingPiece"][];
            /** Walls */
            walls: components["schemas"]["MeshWall"][];
        };
        /**
         * MeshConnection
         * @description A connection marker: where it is and what type it has, with no size or shape (ART-002 §5.2).
         */
        MeshConnection: {
            /** Connection Id */
            connection_id: string;
            /**
             * Connection Type
             * @enum {string}
             */
            connection_type: "PEGGED_MORTISE_TENON" | "BRIDLE" | "HOUSED_DOVETAIL" | "STEEL_KNIFE_PLATE" | "JOIST_HANGER";
            /** Generation Key */
            generation_key: string;
            /**
             * Junction Class
             * @enum {string}
             */
            junction_class: "post-beam" | "post-sill" | "brace" | "joist-beam" | "rafter-peak" | "rafter-foot" | "purlin-rafter";
            /** Location M */
            location_m: number[];
        };
        /** MeshMember */
        MeshMember: {
            /** Axis End M */
            axis_end_m: number[];
            /** Axis Start M */
            axis_start_m: number[];
            /** Generation Key */
            generation_key: string;
            /** Member Id */
            member_id: string;
            /**
             * Primitive
             * @default oriented_box
             * @constant
             */
            primitive: "oriented_box";
            /**
             * Role
             * @enum {string}
             */
            role: "POST" | "BEAM" | "SILL" | "FLOOR_JOIST" | "PRINCIPAL_RAFTER" | "PURLIN" | "KNEE_BRACE";
            /** Section Depth M */
            section_depth_m: number;
            /** Section Width M */
            section_width_m: number;
        };
        /**
         * MeshWall
         * @description One box per layer, with rectangular voids through every layer (ART-003 §6.1). A display primitive.
         */
        MeshWall: {
            /** Base End M */
            base_end_m: number[];
            /** Base Start M */
            base_start_m: number[];
            /** Generation Key */
            generation_key: string;
            /** Height M */
            height_m: number;
            /** Layers */
            layers: components["schemas"]["WallLayerSpan"][];
            /** Outward Xy */
            outward_xy: number[];
            /**
             * Primitive
             * @default layered_wall
             * @constant
             */
            primitive: "layered_wall";
            /** Voids */
            voids: components["schemas"]["WallVoid"][];
            /** Wall Id */
            wall_id: string;
        };
        /**
         * MeshWallFramingPiece
         * @description An oriented box per piece (ART-003 §6.2): through-wall along the wall's ``outward_xy``, in-plane in the
         *     wall's plane across the axis. No key and no ``primitive`` field (D086).
         */
        MeshWallFramingPiece: {
            /** Axis End M */
            axis_end_m: number[];
            /** Axis Start M */
            axis_start_m: number[];
            /** Piece Id */
            piece_id: string;
            /**
             * Piece Kind
             * @enum {string}
             */
            piece_kind: "STUD" | "GIRT" | "KING" | "JACK" | "HEADER" | "ROUGH_SILL" | "CRIPPLE" | "BUCK_JAMB" | "BUCK_HEAD" | "BUCK_SILL";
            /** Section In Plane M */
            section_in_plane_m: number;
            /** Section Through Wall M */
            section_through_wall_m: number;
            /** Wall Id */
            wall_id: string;
        };
        /** Message */
        Message: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** MissingInput */
        MissingInput: {
            /** Assembly Label */
            assembly_label: string;
            /** Fields */
            fields: string[];
            /** Layer */
            layer: string;
        };
        /** NoArgs */
        NoArgs: Record<string, never>;
        /**
         * Opening
         * @description A user-authored rough opening, a void, not a product (D069; MODEL-006 §4.6).
         */
        Opening: {
            /** Height M */
            height_m: number;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "Opening";
            /** Offset M */
            offset_m: number;
            /**
             * Opening Kind
             * @enum {string}
             */
            opening_kind: "WINDOW" | "DOOR";
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Sill Height M */
            sill_height_m: number;
            /** Wall Id */
            wall_id: string;
            /** Width M */
            width_m: number;
        };
        /** OpeningAggregate */
        OpeningAggregate: {
            /** Area M2 */
            area_m2: number;
            /** Count */
            count: number;
            /**
             * Opening Kind
             * @enum {string}
             */
            opening_kind: "WINDOW" | "DOOR";
        };
        /** PathFigure */
        PathFigure: {
            /** Missing Inputs */
            missing_inputs: components["schemas"]["MissingInput"][];
            /** R Value M2 K W */
            r_value_m2_k_w: number | null;
            /** U Value W M2 K */
            u_value_w_m2_k: number | null;
        };
        /** plan2d payload (artifacts.md §5) */
        Plan2dPayload: {
            /** Dimensions */
            dimensions: components["schemas"]["Dimension"][];
            footprint: components["schemas"]["PlanFootprint"];
            /** Planes */
            planes: components["schemas"]["PlanPlane"][];
            roof_plan: components["schemas"]["RoofPlan"];
            /**
             * Units
             * @default m
             * @constant
             */
            units: "m";
        };
        /**
         * PlanConnection
         * @description A connection marker on the entering member's plane (ART-002 §4.2). Members are listed by the schedule.
         */
        PlanConnection: {
            /** Connection Id */
            connection_id: string;
            /**
             * Connection Type
             * @enum {string}
             */
            connection_type: "PEGGED_MORTISE_TENON" | "BRIDLE" | "HOUSED_DOVETAIL" | "STEEL_KNIFE_PLATE" | "JOIST_HANGER";
            /** Generation Key */
            generation_key: string;
            /**
             * Junction Class
             * @enum {string}
             */
            junction_class: "post-beam" | "post-sill" | "brace" | "joist-beam" | "rafter-peak" | "rafter-foot" | "purlin-rafter";
            /** Xy M */
            xy_m: number[];
        };
        /** PlanFootprint */
        PlanFootprint: {
            /** Depth M */
            depth_m: number;
            /** Origin M */
            origin_m: number[];
            /** Ring M */
            ring_m: number[][];
            /** Rotation Rad */
            rotation_rad: number;
            /** Width M */
            width_m: number;
        };
        /**
         * PlanHorizontalPiece
         * @description A girt, header, rough sill, buck head, or buck sill: the plan projection of its axis (D086).
         */
        PlanHorizontalPiece: {
            /** End Xy M */
            end_xy_m: number[];
            /** Piece Id */
            piece_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            piece_kind: "BUCK_HEAD" | "BUCK_SILL" | "GIRT" | "HEADER" | "ROUGH_SILL";
            /** Start Xy M */
            start_xy_m: number[];
        };
        /** PlanLine */
        PlanLine: {
            /** End Xy M */
            end_xy_m: number[];
            /** Start Xy M */
            start_xy_m: number[];
        };
        /**
         * PlanLinearMember
         * @description Every role but posts: the plan projection of the member's axis (ART-002 §4.1).
         */
        PlanLinearMember: {
            /** End Xy M */
            end_xy_m: number[];
            /** Generation Key */
            generation_key: string;
            /** Member Id */
            member_id: string;
            /** Start Xy M */
            start_xy_m: number[];
        };
        /** PlanPlane */
        PlanPlane: {
            /** Beams */
            beams: components["schemas"]["PlanLinearMember"][];
            /** Braces */
            braces: components["schemas"]["PlanLinearMember"][];
            /** Connections */
            connections: components["schemas"]["PlanConnection"][];
            /** Joists */
            joists: components["schemas"]["PlanLinearMember"][];
            /** Level Id */
            level_id: string | null;
            /**
             * Plane Id
             * @enum {string}
             */
            plane_id: "level-0" | "level-1" | "eave" | "roof";
            /** Posts */
            posts: components["schemas"]["PlanPost"][];
            /** Purlins */
            purlins: components["schemas"]["PlanLinearMember"][];
            /** Rafters */
            rafters: components["schemas"]["PlanLinearMember"][];
            /** Sills */
            sills: components["schemas"]["PlanLinearMember"][];
            /** Wall Framing */
            wall_framing: (components["schemas"]["PlanVerticalPiece"] | components["schemas"]["PlanHorizontalPiece"])[];
            /** Walls */
            walls: components["schemas"]["PlanWall"][];
            /** Z M */
            z_m: number;
        };
        /** PlanPost */
        PlanPost: {
            /** Generation Key */
            generation_key: string;
            /** Member Id */
            member_id: string;
            /** Xy M */
            xy_m: number[];
        };
        /**
         * PlanVerticalPiece
         * @description A stud, king, jack, cripple, or buck jamb: the plan projection of its start. No key or section (D086).
         */
        PlanVerticalPiece: {
            /** Piece Id */
            piece_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            piece_kind: "BUCK_JAMB" | "CRIPPLE" | "JACK" | "KING" | "STUD";
            /** Xy M */
            xy_m: number[];
        };
        /**
         * PlanWall
         * @description A wall's outline: the band from start to end, ``exterior_m`` outward and ``interior_m`` inward (D070, D083).
         */
        PlanWall: {
            /** End Xy M */
            end_xy_m: number[];
            /** Exterior M */
            exterior_m: number;
            /** Generation Key */
            generation_key: string;
            /** Interior M */
            interior_m: number;
            /** Openings */
            openings: components["schemas"]["PlanWallOpening"][];
            /** Outward Xy */
            outward_xy: number[];
            /** Start Xy M */
            start_xy_m: number[];
            /** Wall Id */
            wall_id: string;
        };
        /**
         * PlanWallOpening
         * @description A gap through the wall's full thickness at the rough opening, along its reference line (ART-003 §5.2).
         */
        PlanWallOpening: {
            /** End Xy M */
            end_xy_m: number[];
            /** Opening Id */
            opening_id: string;
            /**
             * Opening Kind
             * @enum {string}
             */
            opening_kind: "WINDOW" | "DOOR";
            /** Start Xy M */
            start_xy_m: number[];
        };
        /** preliminary_estimate payload (artifacts.md §8) */
        PreliminaryEstimatePayload: {
            /** Assumptions */
            assumptions: components["schemas"]["Assumption"][];
            /**
             * Coverage
             * @enum {string}
             */
            coverage: "none" | "partial" | "complete";
            /** Currency */
            currency: "USD" | null;
            /** Line Items */
            line_items: (components["schemas"]["TimberLine"] | components["schemas"]["ConnectionLine"] | components["schemas"]["AssemblyLine"] | components["schemas"]["WallFramingLine"])[];
            price_book: components["schemas"]["PriceBookInfo"] | null;
            totals: components["schemas"]["Totals"];
        };
        /** PreviewResponse */
        PreviewResponse: {
            /** Base Revision Id */
            base_revision_id: string;
            /** Changes */
            changes: components["schemas"]["FieldChange"][];
            /** Classification */
            classification: string;
            /** Classification Version */
            classification_version: string;
            /** Command Hash */
            command_hash: string;
            /** Confirmation Required */
            confirmation_required: boolean;
            connections: components["schemas"]["ConnectionChanges"];
            /** Expires At */
            expires_at: string;
            /**
             * Impacted Artifacts
             * @description Exactly the artifact types whose payload for the new revision differs from the base's, sorted; possibly empty (interfaces.md §3, DEP-001 §6). The others are reused unchanged.
             */
            impacted_artifacts: ("plan2d" | "mesh3d" | "timber_schedule" | "assembly_schedule" | "preliminary_estimate")[];
            /** Is Noop */
            is_noop: boolean;
            members: components["schemas"]["MemberChanges"];
            /** Preview Token */
            preview_token: string;
            /** Revision Id */
            revision_id: string | null;
            wall_framing: components["schemas"]["WallFramingChanges"];
            walls: components["schemas"]["WallChanges"];
            /** Warnings */
            warnings: components["schemas"]["PreviewWarning"][];
        };
        /** PreviewWarning */
        PreviewWarning: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /**
         * Price book (artifacts.md §8.2)
         * @description A project's price book as submitted (book-level metadata, artifacts.md §8.2).
         */
        PriceBook: {
            /** As Of */
            as_of: string;
            /**
             * Currency
             * @constant
             */
            currency: "USD";
            /** Geography */
            geography: string;
            /** Rows */
            rows: components["schemas"]["PriceRow"][];
            /** Source */
            source: string;
        };
        /** PriceBookInfo */
        PriceBookInfo: {
            /** As Of */
            as_of: string;
            /**
             * Currency
             * @constant
             */
            currency: "USD";
            /** Geography */
            geography: string;
            /** Price Book Id */
            price_book_id: string;
            /** Price Book Version */
            price_book_version: number;
            /** Source */
            source: string;
        };
        /** PriceBookResponse */
        PriceBookResponse: {
            price_book: components["schemas"]["StoredPriceBook"] | null;
        };
        /** PriceBookSet */
        PriceBookSet: {
            /** Price Book Id */
            price_book_id: string;
            /** Set At */
            set_at: string;
            /** Version */
            version: number;
        };
        /** PriceRow */
        PriceRow: {
            /** Key */
            key: string;
            /**
             * Unit
             * @enum {string}
             */
            unit: "m" | "each" | "m2";
            /** Unit Price Minor */
            unit_price_minor: number;
        };
        /** ProjectList */
        ProjectList: {
            /**
             * Projects
             * @description The caller's own projects, newest first (UI-001 §8.1).
             */
            projects: components["schemas"]["ProjectSummary"][];
        };
        /** ProjectResponse */
        ProjectResponse: {
            /** Created At */
            created_at: string;
            /** Head Revision Id */
            head_revision_id: string;
            /** Head Sequence */
            head_sequence: number;
            /** Permissions */
            permissions: ("read" | "write")[];
            /** Project Id */
            project_id: string;
        };
        /** ProjectSummary */
        ProjectSummary: {
            /** Created At */
            created_at: string;
            /** Head Revision Id */
            head_revision_id: string;
            /** Head Sequence */
            head_sequence: number;
            /** Project Id */
            project_id: string;
        };
        /** RemoveOpening */
        RemoveOpening: {
            args: components["schemas"]["RemoveOpeningArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "RemoveOpening";
        };
        /** RemoveOpeningArgs */
        RemoveOpeningArgs: {
            /** Opening Id */
            opening_id: string;
        };
        /** RevisionList */
        RevisionList: {
            /** Revisions */
            revisions: components["schemas"]["RevisionSummary"][];
        };
        /** RevisionSummary */
        RevisionSummary: {
            /** Command Type */
            command_type: string | null;
            /** Created At */
            created_at: string;
            /** Operation Id */
            operation_id: string | null;
            /** Parent Revision Id */
            parent_revision_id: string | null;
            /** Revision Id */
            revision_id: string;
            /** Sequence */
            sequence: number;
        };
        /**
         * RoleDefault
         * @description Section and material assigned to every generated member of one role (D039).
         */
        RoleDefault: {
            /** Material Id */
            material_id: string;
            /** Section Id */
            section_id: string;
        };
        /** RoofPlan */
        RoofPlan: {
            /** Eave Ring M */
            eave_ring_m: number[][];
            ridge_m: components["schemas"]["PlanLine"];
        };
        /** RoofSurface */
        RoofSurface: {
            /**
             * Id
             * @enum {string}
             */
            id: "south" | "north";
            /** Ring M */
            ring_m: number[][];
        };
        /** ScheduleAggregate */
        ScheduleAggregate: {
            /** Count */
            count: number;
            /** Nominal Section */
            nominal_section: string;
            /**
             * Role
             * @enum {string}
             */
            role: "POST" | "BEAM" | "SILL" | "FLOOR_JOIST" | "PRINCIPAL_RAFTER" | "PURLIN" | "KNEE_BRACE";
            /** Total Length M */
            total_length_m: number;
        };
        /** ScheduleConnectionRow */
        ScheduleConnectionRow: {
            /** Connection Id */
            connection_id: string;
            /**
             * Connection Type
             * @enum {string}
             */
            connection_type: "PEGGED_MORTISE_TENON" | "BRIDLE" | "HOUSED_DOVETAIL" | "STEEL_KNIFE_PLATE" | "JOIST_HANGER";
            /** Generation Key */
            generation_key: string;
            /**
             * Junction Class
             * @enum {string}
             */
            junction_class: "post-beam" | "post-sill" | "brace" | "joist-beam" | "rafter-peak" | "rafter-foot" | "purlin-rafter";
            /** Member Ids */
            member_ids: string[];
            /**
             * Quantity
             * @default 1
             * @constant
             */
            quantity: 1;
        };
        /** ScheduleRow */
        ScheduleRow: {
            /** Generation Key */
            generation_key: string;
            /** Grade */
            grade: string | null;
            /** Length M */
            length_m: number;
            /** Material Id */
            material_id: string;
            /** Member Id */
            member_id: string;
            /** Nominal Section */
            nominal_section: string;
            /**
             * Quantity
             * @default 1
             * @constant
             */
            quantity: 1;
            /**
             * Role
             * @enum {string}
             */
            role: "POST" | "BEAM" | "SILL" | "FLOOR_JOIST" | "PRINCIPAL_RAFTER" | "PURLIN" | "KNEE_BRACE";
            /** Section Id */
            section_id: string;
            /** Species */
            species: string | null;
        };
        /** ScheduleUnits */
        ScheduleUnits: {
            /**
             * Count
             * @default 1
             * @constant
             */
            count: "1";
            /**
             * Length
             * @default m
             * @constant
             */
            length: "m";
        };
        /** Section */
        Section: {
            /** Actual Depth M */
            actual_depth_m: number;
            /** Actual Width M */
            actual_width_m: number;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "Section";
            /** Nominal Label */
            nominal_label: string;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /**
             * Shape
             * @constant
             */
            shape: "rectangular";
        };
        /** SetConnectionType */
        SetConnectionType: {
            args: components["schemas"]["ConnectionTypeArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "SetConnectionType";
        };
        /** SetFootprintDimensions */
        SetFootprintDimensions: {
            args: components["schemas"]["FootprintArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "SetFootprintDimensions";
        };
        /** SetFrameParameters */
        SetFrameParameters: {
            args: components["schemas"]["FrameParametersArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "SetFrameParameters";
        };
        /** SetGableRoofParameters */
        SetGableRoofParameters: {
            args: components["schemas"]["GableRoofArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "SetGableRoofParameters";
        };
        /** SetMemberSection */
        SetMemberSection: {
            args: components["schemas"]["MemberSectionArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "SetMemberSection";
        };
        /** SetOpening */
        SetOpening: {
            args: components["schemas"]["SetOpeningArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "SetOpening";
        };
        /**
         * SetOpeningArgs
         * @description Replaces one opening's dimensions and position in its own wall; its kind and wall do not change.
         */
        SetOpeningArgs: {
            /** Height M */
            height_m: number;
            /** Offset M */
            offset_m: number;
            /** Opening Id */
            opening_id: string;
            /** Sill Height M */
            sill_height_m: number;
            /** Width M */
            width_m: number;
        };
        /** SetStoryHeights */
        SetStoryHeights: {
            args: components["schemas"]["StoryHeightsArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "SetStoryHeights";
        };
        /** SetTimberGrid */
        SetTimberGrid: {
            args: components["schemas"]["TimberGridArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "SetTimberGrid";
        };
        /** SetWallAssembly */
        SetWallAssembly: {
            args: components["schemas"]["WallAssemblyArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "SetWallAssembly";
        };
        /**
         * Semantic building snapshot (model schema version 3)
         * @description A semantic snapshot, model schema version 3 (building-model.md §3, §3.3, §3.4).
         */
        Snapshot: {
            building: components["schemas"]["Building"];
            /** Created At */
            created_at: string;
            /** Entities */
            entities: (components["schemas"]["Building"] | components["schemas"]["Footprint"] | components["schemas"]["Level"] | components["schemas"]["GableRoof"] | components["schemas"]["TimberGrid"] | components["schemas"]["FrameSystem"] | components["schemas"]["TimberMember"] | components["schemas"]["Connection"] | components["schemas"]["Section"] | components["schemas"]["Material"] | components["schemas"]["WallSystem"] | components["schemas"]["AssemblyDefinition"] | components["schemas"]["Wall"] | components["schemas"]["WallFramingPiece"] | components["schemas"]["Opening"])[];
            /**
             * Model Schema Version
             * @constant
             */
            model_schema_version: 3;
            /** Parent Revision Id */
            parent_revision_id: string | null;
            /** Project Id */
            project_id: string;
            /** Revision Id */
            revision_id: string;
        };
        /** StoredPriceBook */
        StoredPriceBook: {
            book: components["schemas"]["PriceBook"];
            /** Price Book Id */
            price_book_id: string;
            /** Set At */
            set_at: string;
            /** Set By */
            set_by: string;
            /** Version */
            version: number;
        };
        /** StoryHeightsArgs */
        StoryHeightsArgs: {
            /** Story Heights M */
            story_heights_m: number[];
        };
        /**
         * StudFraming
         * @description A stud infill framing layer (D066, D067; MODEL-006 §4.3). Kings, jacks, cripples, and rough sills take the stud section (D076).
         */
        StudFraming: {
            /** Framing Material Id */
            framing_material_id: string;
            framing_thermal_conductivity_w_m_k: components["schemas"]["DeclaredValue"] | null;
            /** Girt Count */
            girt_count: number;
            /** Girt Section Id */
            girt_section_id: string | null;
            /** Header Section Id */
            header_section_id: string;
            /** Jack Threshold Width M */
            jack_threshold_width_m: number;
            /** Stud Section Id */
            stud_section_id: string;
            /** Stud Spacing M */
            stud_spacing_m: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "STUD";
        };
        /** StudFramingSummary */
        StudFramingSummary: {
            /** Framing Material Id */
            framing_material_id: string;
            /** Framing Material Name */
            framing_material_name: string;
            framing_thermal_conductivity_w_m_k: components["schemas"]["DeclaredValue"] | null;
            /** Girt Count */
            girt_count: number;
            /** Girt Section */
            girt_section: string | null;
            /** Header Section */
            header_section: string;
            /** Jack Threshold Width M */
            jack_threshold_width_m: number;
            /** Stud Section */
            stud_section: string;
            /** Stud Spacing M */
            stud_spacing_m: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "STUD";
        };
        /** ThermalDefinition */
        ThermalDefinition: {
            /** Assembly Label */
            assembly_label: string;
            center_of_cavity: components["schemas"]["PathFigure"];
            framing_path: components["schemas"]["PathFigure"];
            parallel_path: components["schemas"]["AreaWeightedFigure"];
        };
        /** ThermalFigures */
        ThermalFigures: {
            all_walls: components["schemas"]["AreaWeightedFigure"];
            /** Definitions */
            definitions: components["schemas"]["ThermalDefinition"][];
            method: components["schemas"]["ThermalMethod"];
        };
        /** ThermalMethod */
        ThermalMethod: {
            /**
             * Id
             * @constant
             */
            id: "parallel-path-1";
            /** Notes */
            notes: string[];
        };
        /** TimberGrid */
        TimberGrid: {
            /** Generation Rule Version */
            generation_rule_version: string;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "TimberGrid";
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** X Lines */
            x_lines: components["schemas"]["XGridLine"][];
            /** Y Lines */
            y_lines: components["schemas"]["YGridLine"][];
        };
        /** TimberGridArgs */
        TimberGridArgs: {
            /** X Lines */
            x_lines: components["schemas"]["GridLineArg"][];
            /** Y Lines */
            y_lines: components["schemas"]["GridLineArg"][];
        };
        /** TimberLine */
        TimberLine: {
            /** Amount Minor */
            amount_minor: number | null;
            /** Key */
            key: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "timber";
            /** Nominal Section */
            nominal_section: string;
            /** Priced */
            priced: boolean;
            /**
             * Quantity Unit
             * @constant
             */
            quantity_unit: "m";
            /** Quantity Value */
            quantity_value: number;
            /**
             * Role
             * @enum {string}
             */
            role: "POST" | "BEAM" | "SILL" | "FLOOR_JOIST" | "PRINCIPAL_RAFTER" | "PURLIN" | "KNEE_BRACE";
            /** Unit Price Minor */
            unit_price_minor: number | null;
        };
        /** TimberMember */
        TimberMember: {
            /** End M */
            end_m: number[];
            /** Generation Key */
            generation_key: string;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "TimberMember";
            /** Material Id */
            material_id: string;
            /**
             * Member Role
             * @enum {string}
             */
            member_role: "POST" | "BEAM" | "SILL" | "FLOOR_JOIST" | "PRINCIPAL_RAFTER" | "PURLIN" | "KNEE_BRACE";
            /**
             * Schema Version
             * @constant
             */
            schema_version: 2;
            /** Section Id */
            section_id: string;
            /** Start M */
            start_m: number[];
        };
        /** timber_schedule payload (artifacts.md §7) */
        TimberSchedulePayload: {
            /** Aggregates */
            aggregates: components["schemas"]["ScheduleAggregate"][];
            /** Assumptions */
            assumptions: components["schemas"]["Assumption"][];
            /** Connection Aggregates */
            connection_aggregates: components["schemas"]["ConnectionAggregate"][];
            connection_catalog: components["schemas"]["ConnectionCatalog"];
            /** Connections */
            connections: components["schemas"]["ScheduleConnectionRow"][];
            /**
             * Length Basis
             * @default reference_axis
             * @constant
             */
            length_basis: "reference_axis";
            /** Members */
            members: components["schemas"]["ScheduleRow"][];
            /**
             * @default {
             *       "count": "1",
             *       "length": "m"
             *     }
             */
            units: components["schemas"]["ScheduleUnits"];
        };
        /** Totals */
        Totals: {
            /** Grand Total Minor */
            grand_total_minor: number | null;
            /** Priced Amount Minor */
            priced_amount_minor: number | null;
            /** Unpriced Line Count */
            unpriced_line_count: number;
        };
        /** UndoArgs */
        UndoArgs: {
            /** Target Revision Id */
            target_revision_id: string;
        };
        /** UndoToRevision */
        UndoToRevision: {
            args: components["schemas"]["UndoArgs"];
            /** Base Revision Id */
            base_revision_id: string;
            /** Command Id */
            command_id: string;
            /** Project Id */
            project_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "UndoToRevision";
        };
        /**
         * Wall
         * @description A generated wall in one perimeter bay of one story (D065; MODEL-006 §4.4).
         */
        Wall: {
            /** Assembly Definition Id */
            assembly_definition_id: string;
            /** End M */
            end_m: number[];
            /** Framing Ids */
            framing_ids: string[];
            /** Generation Key */
            generation_key: string;
            /** Height M */
            height_m: number;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "Wall";
            /** Level Id */
            level_id: string;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Start M */
            start_m: number[];
        };
        /**
         * WallAssemblyArgs
         * @description D068: one project-wide wall assembly (MODEL-006 §8.1).
         */
        WallAssemblyArgs: {
            /** Assembly Definition Id */
            assembly_definition_id: string;
        };
        /**
         * WallChanges
         * @description Generated walls the commit adds, removes, or changes (MODEL-006 §8.6), shaped like `members`.
         */
        WallChanges: {
            /** Added */
            added: components["schemas"]["WallRef"][];
            /** Removed */
            removed: components["schemas"]["WallRef"][];
            /** Updated */
            updated: string[];
        };
        /**
         * WallFramingChanges
         * @description Generated wall framing pieces the commit adds, removes, or changes (MODEL-006 §8.6), shaped like `members`.
         */
        WallFramingChanges: {
            /** Added */
            added: components["schemas"]["WallFramingRef"][];
            /** Removed */
            removed: components["schemas"]["WallFramingRef"][];
            /** Updated */
            updated: string[];
        };
        /**
         * WallFramingLine
         * @description One line per wall framing kind and section in use, priced per meter, with its count beside (D070).
         */
        WallFramingLine: {
            /** Amount Minor */
            amount_minor: number | null;
            /** Count */
            count: number;
            /** Key */
            key: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "wallframing";
            /** Nominal Section */
            nominal_section: string;
            /**
             * Piece Kind
             * @enum {string}
             */
            piece_kind: "STUD" | "GIRT" | "KING" | "JACK" | "HEADER" | "ROUGH_SILL" | "CRIPPLE" | "BUCK_JAMB" | "BUCK_HEAD" | "BUCK_SILL";
            /** Priced */
            priced: boolean;
            /**
             * Quantity Unit
             * @constant
             */
            quantity_unit: "m";
            /** Quantity Value */
            quantity_value: number;
            /** Unit Price Minor */
            unit_price_minor: number | null;
        };
        /**
         * WallFramingPiece
         * @description One generated wall framing piece (D066; MODEL-006 §4.5). No connection records.
         */
        WallFramingPiece: {
            /** End M */
            end_m: number[];
            /** Generation Key */
            generation_key: string;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "WallFramingPiece";
            /** Material Id */
            material_id: string;
            /** Opening Id */
            opening_id: string | null;
            /**
             * Piece Kind
             * @enum {string}
             */
            piece_kind: "STUD" | "GIRT" | "KING" | "JACK" | "HEADER" | "ROUGH_SILL" | "CRIPPLE" | "BUCK_JAMB" | "BUCK_HEAD" | "BUCK_SILL";
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Section Id */
            section_id: string;
            /** Start M */
            start_m: number[];
        };
        /** WallFramingRef */
        WallFramingRef: {
            /** Generation Key */
            generation_key: string;
            /** Id */
            id: string;
        };
        /** WallFramingRow */
        WallFramingRow: {
            /** Generation Key */
            generation_key: string;
            /** Grade */
            grade: string | null;
            /** Length M */
            length_m: number;
            /** Material Id */
            material_id: string;
            /** Nominal Section */
            nominal_section: string;
            /** Opening Id */
            opening_id: string | null;
            /** Piece Id */
            piece_id: string;
            /**
             * Piece Kind
             * @enum {string}
             */
            piece_kind: "STUD" | "GIRT" | "KING" | "JACK" | "HEADER" | "ROUGH_SILL" | "CRIPPLE" | "BUCK_JAMB" | "BUCK_HEAD" | "BUCK_SILL";
            /**
             * Quantity
             * @default 1
             * @constant
             */
            quantity: 1;
            /** Section Id */
            section_id: string;
            /** Species */
            species: string | null;
            /** Wall Id */
            wall_id: string;
        };
        /**
         * WallLayerSpan
         * @description A layer's signed interval along the wall's outward normal, 0 at the reference plane (D083).
         */
        WallLayerSpan: {
            /**
             * Function
             * @enum {string}
             */
            function: "FINISH" | "SHEATHING" | "INSULATION" | "FRAMING";
            /** Inner M */
            inner_m: number;
            /** Name */
            name: string;
            /** Outer M */
            outer_m: number;
        };
        /** WallRef */
        WallRef: {
            /** Generation Key */
            generation_key: string;
            /** Id */
            id: string;
        };
        /**
         * WallSystem
         * @description The wall rule version, D068's project-wide default definition, and the walls and openings (D073).
         */
        WallSystem: {
            /** Default Assembly Definition Id */
            default_assembly_definition_id: string;
            /** Generation Rule Version */
            generation_rule_version: string;
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "WallSystem";
            /** Opening Ids */
            opening_ids: string[];
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Wall Ids */
            wall_ids: string[];
        };
        /**
         * WallVoid
         * @description A rough opening in wall-local coordinates: ``u`` along the wall from its start, ``v`` up from its base.
         */
        WallVoid: {
            /** Opening Id */
            opening_id: string;
            /**
             * Opening Kind
             * @enum {string}
             */
            opening_kind: "WINDOW" | "DOOR";
            /** U M */
            u_m: number[];
            /** V M */
            v_m: number[];
        };
        /**
         * XGridLine
         * @description A grid line across X with a stable identity (D042).
         */
        XGridLine: {
            /** Fraction */
            fraction: number;
            /** Id */
            id: string;
        };
        /**
         * YGridLine
         * @description A grid line across Y with a stable identity (D042).
         */
        YGridLine: {
            /** Fraction */
            fraction: number;
            /** Id */
            id: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    listProjects: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The projects. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectList"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    createProject: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description The creation envelope. */
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateProjectRequest"];
            };
        };
        responses: {
            /** @description Idempotent retry (`replayed: true`). */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommitResponse"];
                };
            };
            /** @description Created. */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommitResponse"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description REVISION_CONFLICT, IDEMPOTENCY_CONFLICT, PREVIEW_INVALID, or PREVIEW_EXPIRED. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description The body is not application/json. */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description VALIDATION_FAILED or UNSUPPORTED_CONFIGURATION, with details. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    getProject: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The project. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectResponse"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Project, revision, or artifact type not found, or not visible to the caller (D050). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    getArtifactManifest: {
        parameters: {
            query?: {
                revision_id?: string | null;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The manifest. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Manifest"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Project, revision, or artifact type not found, or not visible to the caller (D050). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    getArtifact: {
        parameters: {
            query?: {
                revision_id?: string | null;
            };
            header?: never;
            path: {
                project_id: string;
                artifact_type: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description CURRENT, UNAVAILABLE (partial payload when provided), or FAILED (with error). */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ArtifactEnvelope"];
                };
            };
            /** @description MISSING: no registered derivation; no payload. */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ArtifactEnvelope"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Project, revision, or artifact type not found, or not visible to the caller (D050). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    commitCommand: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        /** @description The command and, when required, its preview token. */
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommitRequest"];
            };
        };
        responses: {
            /** @description A no-op (D045) or an idempotent retry (`replayed: true`). */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommitResponse"];
                };
            };
            /** @description A new revision. */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommitResponse"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Project, revision, or artifact type not found, or not visible to the caller (D050). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description REVISION_CONFLICT, IDEMPOTENCY_CONFLICT, PREVIEW_INVALID, or PREVIEW_EXPIRED. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description The body is not application/json. */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description VALIDATION_FAILED or UNSUPPORTED_CONFIGURATION, with details. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description PREVIEW_REQUIRED: a consequential command needs a preview token. */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    previewCommand: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        /** @description A command envelope. */
        requestBody: {
            content: {
                "application/json": components["schemas"]["Command"];
            };
        };
        responses: {
            /** @description The proposed change and a preview token. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PreviewResponse"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Project, revision, or artifact type not found, or not visible to the caller (D050). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description REVISION_CONFLICT, IDEMPOTENCY_CONFLICT, PREVIEW_INVALID, or PREVIEW_EXPIRED. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description The body is not application/json. */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description VALIDATION_FAILED or UNSUPPORTED_CONFIGURATION, with details. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    getPriceBook: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The current version. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PriceBookResponse"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Project, revision, or artifact type not found, or not visible to the caller (D050). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    setPriceBook: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        /** @description The price book. */
        requestBody: {
            content: {
                "application/json": components["schemas"]["PriceBook"];
            };
        };
        responses: {
            /** @description The new version. */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PriceBookSet"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Project, revision, or artifact type not found, or not visible to the caller (D050). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description The body is not application/json. */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description VALIDATION_FAILED or UNSUPPORTED_CONFIGURATION, with details. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    listRevisions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The revisions. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevisionList"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Project, revision, or artifact type not found, or not visible to the caller (D050). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    getRevision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                revision_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The snapshot. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Snapshot"];
                };
            };
            /** @description Missing or unknown bearer token (UNAUTHORIZED). */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Project, revision, or artifact type not found, or not visible to the caller (D050). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Any other error, including 500 INTERNAL. */
            default: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
}
