-- EST-001 §5 / artifacts.md §8.2: versioned, append-only price books per project.

CREATE TABLE price_books (
    project_id     uuid NOT NULL REFERENCES projects (project_id),
    version        integer NOT NULL CHECK (version >= 1),
    price_book_id  uuid NOT NULL,
    book           jsonb NOT NULL,
    set_by         uuid NOT NULL,
    set_at         timestamptz NOT NULL,
    PRIMARY KEY (project_id, version)
);

CREATE TRIGGER price_books_append_only BEFORE UPDATE OR DELETE ON price_books
    FOR EACH ROW EXECUTE FUNCTION homedesign_reject_mutation();
CREATE TRIGGER price_books_no_truncate BEFORE TRUNCATE ON price_books
    FOR EACH STATEMENT EXECUTE FUNCTION homedesign_reject_mutation();
