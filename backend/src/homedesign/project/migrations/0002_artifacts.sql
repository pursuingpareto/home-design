-- ART-001 §5 / building-model.md §7: derived artifacts. Recomputable data, NOT append-only.

CREATE TABLE artifacts (
    project_id         uuid NOT NULL REFERENCES projects (project_id),
    revision_id        uuid NOT NULL REFERENCES revisions (revision_id),
    artifact_type      text NOT NULL,
    input_fingerprint  text NOT NULL,
    generator_id       text NOT NULL,
    generator_version  text NOT NULL,
    status             text NOT NULL CHECK (status IN ('CURRENT', 'UNAVAILABLE', 'FAILED')),
    payload            jsonb NULL,
    error              jsonb NULL,
    warnings           jsonb NOT NULL DEFAULT '[]'::jsonb,
    generated_at       timestamptz NOT NULL,
    PRIMARY KEY (revision_id, artifact_type, input_fingerprint)
);
