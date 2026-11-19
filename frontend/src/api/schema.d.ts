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
        /**
         * VS-01 artifact envelope (artifacts.md §2)
         * @description Common envelope for every artifact response (artifacts.md §2).
         */
        ArtifactEnvelope: {
            /**
             * Artifact Type
             * @enum {string}
             */
            artifact_type: "plan2d" | "mesh3d" | "timber_schedule" | "preliminary_estimate";
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
        /** Assumption */
        Assumption: {
            /** Code */
            code: string;
            /** Message */
            message: string;
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
            schema_version: 1;
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
        Command: components["schemas"]["CreateReferenceProject"] | components["schemas"]["SetFootprintDimensions"] | components["schemas"]["SetStoryHeights"] | components["schemas"]["SetGableRoofParameters"] | components["schemas"]["SetTimberGrid"] | components["schemas"]["SetMemberSection"] | components["schemas"]["AddSection"] | components["schemas"]["UndoToRevision"];
        /** CommitRequest */
        CommitRequest: {
            /** Command */
            command: components["schemas"]["CreateReferenceProject"] | components["schemas"]["SetFootprintDimensions"] | components["schemas"]["SetStoryHeights"] | components["schemas"]["SetGableRoofParameters"] | components["schemas"]["SetTimberGrid"] | components["schemas"]["SetMemberSection"] | components["schemas"]["AddSection"] | components["schemas"]["UndoToRevision"];
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
        /** FrameSystem */
        FrameSystem: {
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
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
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
            /**
             * Id
             * @default null
             */
            id: string | null;
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
        /** LineItem */
        LineItem: {
            /** Amount Minor */
            amount_minor: number | null;
            /** Key */
            key: string;
            /** Nominal Section */
            nominal_section: string;
            /** Priced */
            priced: boolean;
            /**
             * Quantity Unit
             * @default m
             * @constant
             */
            quantity_unit: "m";
            /** Quantity Value */
            quantity_value: number;
            /** Role */
            role: string;
            /** Unit Price Minor */
            unit_price_minor: number | null;
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
            role: "POST" | "BEAM" | "FLOOR_JOIST" | "RAFTER";
            /** Section Id */
            section_id: string;
        };
        /** mesh3d payload (artifacts.md §6) */
        Mesh3dPayload: {
            envelope: components["schemas"]["Envelope3d"];
            /** Members */
            members: components["schemas"]["MeshMember"][];
            /**
             * Units
             * @default m
             * @constant
             */
            units: "m";
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
            role: "POST" | "BEAM" | "FLOOR_JOIST" | "RAFTER";
            /** Section Depth M */
            section_depth_m: number;
            /** Section Width M */
            section_width_m: number;
        };
        /** Message */
        Message: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** NoArgs */
        NoArgs: Record<string, never>;
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
        /** PlanBeam */
        PlanBeam: {
            /** End Xy M */
            end_xy_m: number[];
            /** Generation Key */
            generation_key: string;
            /** Member Id */
            member_id: string;
            /** Section Id */
            section_id: string;
            /** Start Xy M */
            start_xy_m: number[];
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
        /** PlanLine */
        PlanLine: {
            /** End Xy M */
            end_xy_m: number[];
            /** Start Xy M */
            start_xy_m: number[];
        };
        /** PlanPlane */
        PlanPlane: {
            /** Beams */
            beams: components["schemas"]["PlanBeam"][];
            /** Level Id */
            level_id: string | null;
            /**
             * Plane Id
             * @enum {string}
             */
            plane_id: "level-0" | "level-1" | "eave";
            /** Posts */
            posts: components["schemas"]["PlanPost"][];
            /** Z M */
            z_m: number;
        };
        /** PlanPost */
        PlanPost: {
            /** Generation Key */
            generation_key: string;
            /** Member Id */
            member_id: string;
            /** Section Id */
            section_id: string;
            /** Xy M */
            xy_m: number[];
        };
        /** preliminary_estimate payload (artifacts.md §8) */
        PreliminaryEstimatePayload: {
            /**
             * Coverage
             * @enum {string}
             */
            coverage: "none" | "partial" | "complete";
            /** Currency */
            currency: "USD" | null;
            /** Line Items */
            line_items: components["schemas"]["LineItem"][];
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
            /** Expires At */
            expires_at: string;
            /** Impacted Artifacts */
            impacted_artifacts: string[];
            /** Is Noop */
            is_noop: boolean;
            members: components["schemas"]["MemberChanges"];
            /** Preview Token */
            preview_token: string;
            /** Revision Id */
            revision_id: string | null;
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
             * @constant
             */
            unit: "m";
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
            role: "POST" | "BEAM" | "FLOOR_JOIST" | "RAFTER";
            /** Total Length M */
            total_length_m: number;
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
            role: "POST" | "BEAM" | "FLOOR_JOIST" | "RAFTER";
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
        /**
         * VS-01 semantic building snapshot (model schema version 1)
         * @description A VS-01 semantic snapshot (building-model.md §3).
         */
        Snapshot: {
            building: components["schemas"]["Building"];
            /** Created At */
            created_at: string;
            /** Entities */
            entities: (components["schemas"]["Building"] | components["schemas"]["Footprint"] | components["schemas"]["Level"] | components["schemas"]["GableRoof"] | components["schemas"]["TimberGrid"] | components["schemas"]["FrameSystem"] | components["schemas"]["TimberMember"] | components["schemas"]["Section"] | components["schemas"]["Material"])[];
            /**
             * Model Schema Version
             * @constant
             */
            model_schema_version: 1;
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
            member_role: "POST" | "BEAM" | "FLOOR_JOIST" | "RAFTER";
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
        /** timber_schedule payload (artifacts.md §7) */
        TimberSchedulePayload: {
            /** Aggregates */
            aggregates: components["schemas"]["ScheduleAggregate"][];
            /** Assumptions */
            assumptions: components["schemas"]["Assumption"][];
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
