-- 003: DOCUMENT CHUNKS AND EMBEDDING STORAGE

CREATE TABLE document_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL
        REFERENCES documents(document_id)
        ON DELETE CASCADE,

    chunk_index INTEGER NOT NULL
        CHECK (chunk_index >= 0),

    page_number INTEGER
        CHECK (page_number IS NULL OR page_number >= 1),

    start_char INTEGER
        CHECK (start_char IS NULL OR start_char >= 0),

    end_char INTEGER
        CHECK (end_char IS NULL OR end_char >= 0),

    section_title TEXT,

    content TEXT NOT NULL
        CHECK (length(btrim(content)) > 0),

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Reserved for Gemini Embedding 2.
    embedding vector(768),

    embedding_model TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (document_id, chunk_index),

    CHECK (
        start_char IS NULL
        OR end_char IS NULL
        OR end_char > start_char
    ),

    CHECK (
        (embedding IS NULL AND embedding_model IS NULL)
        OR
        (embedding IS NOT NULL AND embedding_model IS NOT NULL)
    )
);

CREATE INDEX idx_document_chunks_document_id
    ON document_chunks(document_id);
