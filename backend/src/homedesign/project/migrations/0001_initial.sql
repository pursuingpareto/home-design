-- MODEL-004 §5 / building-model.md §7: projects, immutable revisions, append-only operations.

CREATE TABLE projects (
    project_id        uuid PRIMARY KEY,
    head_revision_id  uuid NOT NULL,
    head_sequence     integer NOT NULL CHECK (head_sequence >= 1),
    created_at        timestamptz NOT NULL,
    created_by        uuid NOT NULL
);

CREATE TABLE revisions (
    revision_id           uuid PRIMARY KEY,
    project_id            uuid NOT NULL REFERENCES projects (project_id),
    parent_revision_id    uuid NULL REFERENCES revisions (revision_id),
    sequence              integer NOT NULL CHECK (sequence >= 1),
    model_schema_version  integer NOT NULL,
    snapshot              jsonb NOT NULL,
    fingerprint           text NOT NULL,
    created_at            timestamptz NOT NULL,
    UNIQUE (project_id, sequence)
);

-- The project row is inserted before its first revision, so this check waits for commit.
ALTER TABLE projects
    ADD CONSTRAINT projects_head_revision_fk
    FOREIGN KEY (head_revision_id) REFERENCES revisions (revision_id)
    DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE operations (
    log_position            bigint GENERATED ALWAYS AS IDENTITY UNIQUE,  -- append order of the audit log
    operation_id            uuid PRIMARY KEY,
    project_id              uuid NULL REFERENCES projects (project_id),
    actor_id                uuid NOT NULL,
    command_id              uuid NULL,
    command_type            text NULL,
    command                 jsonb NULL,
    command_hash            text NULL,
    base_revision_id        uuid NULL,
    result                  text NOT NULL CHECK (result IN ('committed', 'noop', 'rejected')),
    rejection_code          text NULL,
    revision_id             uuid NULL REFERENCES revisions (revision_id),
    classification          text NULL,
    classification_version  text NULL,
    created_at              timestamptz NOT NULL,
    CHECK ((result = 'rejected') = (rejection_code IS NOT NULL))
);

-- Idempotency (interfaces.md §2): only successful attempts reserve a command_id.
CREATE UNIQUE INDEX operations_command_idempotency
    ON operations (project_id, actor_id, command_id)
    WHERE result IN ('committed', 'noop') AND command_type <> 'CreateReferenceProject';
CREATE UNIQUE INDEX operations_creation_idempotency
    ON operations (actor_id, command_id)
    WHERE result = 'committed' AND command_type = 'CreateReferenceProject';
CREATE INDEX operations_by_revision ON operations (revision_id);
CREATE INDEX operations_by_project ON operations (project_id, log_position);

-- Immutability (D026): revisions and operations are append-only.
CREATE FUNCTION homedesign_reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TRIGGER revisions_append_only BEFORE UPDATE OR DELETE ON revisions
    FOR EACH ROW EXECUTE FUNCTION homedesign_reject_mutation();
CREATE TRIGGER revisions_no_truncate BEFORE TRUNCATE ON revisions
    FOR EACH STATEMENT EXECUTE FUNCTION homedesign_reject_mutation();
CREATE TRIGGER operations_append_only BEFORE UPDATE OR DELETE ON operations
    FOR EACH ROW EXECUTE FUNCTION homedesign_reject_mutation();
CREATE TRIGGER operations_no_truncate BEFORE TRUNCATE ON operations
    FOR EACH STATEMENT EXECUTE FUNCTION homedesign_reject_mutation();
