-- 004: DOCUMENT ARCHIVAL
-- Preserve uploaded resources while excluding archived material from retrieval.

ALTER TABLE documents
ADD COLUMN archived_at TIMESTAMPTZ;

CREATE INDEX idx_documents_active_course
ON documents(course_id)
WHERE archived_at IS NULL;
