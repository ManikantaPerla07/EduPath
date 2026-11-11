# EduPath RAG Retrieval Evaluation

This directory contains a small, repeatable benchmark for the beginner Python knowledge base.

## Golden-query benchmark

`retrieval_golden_queries.json` contains 18 original evaluation questions: two for each of the nine Python course topics. Each case includes an ID, query, and expected topic slug.

The evaluator deliberately searches the whole published course. It does **not** pass the expected topic as a retrieval filter. This lets the benchmark measure whether semantic retrieval ranks a chunk associated with the expected topic.

## Metrics

- **Retrieval coverage:** percentage of golden queries for which at least one chunk was returned.
- **Hit@K:** percentage of queries with at least one expected-topic chunk in the first K results.
- **Precision@K:** expected-topic chunks among the first K result positions divided by K times the number of queries. Missing result positions count as non-relevant.
- **MRR (Mean Reciprocal Rank):** average of the reciprocal rank of the first expected-topic chunk. A query with no expected-topic chunk contributes zero.
- **Per-topic metrics:** the same metrics calculated for the two benchmark queries assigned to each expected topic.

A chunk is considered relevant for this benchmark when its `topic_slug` exactly matches the case's `expected_topic_slug`. Course-wide resources have no topic slug and do not count as a topic match.

## Run after final knowledge-base ingestion

Do not run the live evaluator during the implementation phase. It requires a published course with its approved learning resources fully processed and embedded.

After the final upload, embedding, administrator review and course publication steps are complete, run from the repository root:

```powershell
python -m evaluation.run_retrieval_evaluation
```

To preserve a machine-readable report outside the repository:

```powershell
python -m evaluation.run_retrieval_evaluation --output .\retrieval-evaluation.json
```

The runner makes one Gemini query-embedding request per golden query and performs a course-wide Neon pgvector search. It does not upload documents, generate tutor answers, or change the database.

A zero-result report exits with a non-zero status and asks the operator to verify publication and embedding readiness. Transient model, network or database failures also stop the evaluation rather than silently producing a partial score.

## What the benchmark does not measure

These are metadata-based retrieval-alignment metrics, not a complete RAG quality score. They do not verify whether a retrieved chunk is factually correct, sufficiently detailed, pedagogically useful, or actually supports a generated answer. They also do not validate generated citations or measure answer faithfulness. Those checks require a later review of actual retrieved excerpts and tutor responses after the corpus is available.

Review the query set as course content evolves. If topics or learning objectives change, update the benchmark and its tests together.
