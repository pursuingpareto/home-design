-- DEP-001 §7.2: reuse looks up a stored artifact by project, type, and input fingerprint, across revisions.

CREATE INDEX artifacts_reuse_idx ON artifacts (project_id, artifact_type, input_fingerprint);
