-- UI-001 §8.1: list an owner's projects, newest first.

CREATE INDEX projects_created_by_created_at_idx ON projects (created_by, created_at DESC, project_id);
