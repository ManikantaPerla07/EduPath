"""Offline-testable evaluation metrics for EduPath course retrieval."""

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any


MIN_EVALUATION_K = 1
MAX_EVALUATION_K = 20
DEFAULT_EVALUATION_KS = (1, 3, 5)


def _validate_course_slug(course_slug: str) -> str:
    """Validate the course slug used for every golden query."""

    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")
    return course_slug.strip()


def _validate_ks(ks: Sequence[int]) -> tuple[int, ...]:
    """Validate unique positive retrieval cutoffs in ascending order."""

    if not isinstance(ks, Sequence) or isinstance(ks, (str, bytes)):
        raise ValueError("Evaluation cutoffs must be a sequence of integers.")

    if not ks:
        raise ValueError("At least one evaluation cutoff is required.")

    normalized = tuple(ks)

    for cutoff in normalized:
        if (
            isinstance(cutoff, bool)
            or not isinstance(cutoff, int)
            or not MIN_EVALUATION_K <= cutoff <= MAX_EVALUATION_K
        ):
            raise ValueError(
                f"Each evaluation cutoff must be between "
                f"{MIN_EVALUATION_K} and {MAX_EVALUATION_K}."
            )

    if tuple(sorted(set(normalized))) != normalized:
        raise ValueError(
            "Evaluation cutoffs must be unique and in ascending order."
        )

    return normalized


def _validate_cases(
    cases: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Validate and normalize a non-empty golden-query collection."""

    if (
        not isinstance(cases, Sequence)
        or isinstance(cases, (str, bytes))
        or not cases
    ):
        raise ValueError("At least one golden retrieval case is required.")

    normalized = []
    seen_ids = set()

    for index, case in enumerate(cases, start=1):
        if not isinstance(case, Mapping):
            raise ValueError(f"Golden case {index} must be a mapping.")

        case_id = case.get("id")
        query = case.get("query")
        expected_topic_slug = case.get("expected_topic_slug")

        for field_name, value in (
            ("id", case_id),
            ("query", query),
            ("expected_topic_slug", expected_topic_slug),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Golden case {index} requires a non-empty {field_name}."
                )

        case_id = case_id.strip()
        if case_id in seen_ids:
            raise ValueError(f"Duplicate golden case ID: {case_id}.")
        seen_ids.add(case_id)

        normalized.append({
            "id": case_id,
            "query": query.strip(),
            "expected_topic_slug": expected_topic_slug.strip(),
        })

    return normalized


def _calculate_metrics(
    first_relevant_ranks: list[int | None],
    relevant_counts_at_k: list[int],
    cutoffs: tuple[int, ...],
    retrieved_count: int,
) -> dict[str, Any]:
    """Calculate standard ranking metrics for one group of queries."""

    query_count = len(first_relevant_ranks)

    hit_rate_at_k = {}
    precision_at_k = {}

    for cutoff in cutoffs:
        hits = sum(
            rank is not None and rank <= cutoff
            for rank in first_relevant_ranks
        )
        relevant_results = relevant_counts_at_k[cutoffs.index(cutoff)]

        hit_rate_at_k[str(cutoff)] = hits / query_count
        # Precision@K uses K result positions per query, including missing
        # positions when fewer than K chunks are returned.
        precision_at_k[str(cutoff)] = (
            relevant_results / (query_count * cutoff)
        )

    reciprocal_ranks = [
        1 / rank if rank is not None else 0.0
        for rank in first_relevant_ranks
    ]

    return {
        "query_count": query_count,
        "queries_with_results": retrieved_count,
        "retrieval_coverage_percent": (
            retrieved_count / query_count
        ) * 100,
        "hit_rate_at_k": hit_rate_at_k,
        "precision_at_k": precision_at_k,
        "mean_reciprocal_rank": sum(reciprocal_ranks) / query_count,
    }


def evaluate_retrieval_cases(
    cases: Sequence[Mapping[str, Any]],
    search_fn: Callable[..., list[dict[str, Any]]],
    course_slug: str,
    ks: Sequence[int] = DEFAULT_EVALUATION_KS,
) -> dict[str, Any]:
    """
    Evaluate course-wide retrieval against expected topic metadata.

    Each golden query is searched without a topic filter. A retrieved chunk
    is considered relevant when its topic_slug matches the case's expected
    topic. This measures topic-level retrieval alignment, not answer quality
    or the factual correctness of the retrieved text.
    """

    normalized_cases = _validate_cases(cases)
    course_slug = _validate_course_slug(course_slug)
    cutoffs = _validate_ks(ks)
    max_k = max(cutoffs)

    case_results = []
    topic_ranks: dict[str, list[int | None]] = defaultdict(list)
    topic_relevant_counts: dict[str, list[int]] = defaultdict(
        lambda: [0] * len(cutoffs)
    )
    topic_retrieved_counts: dict[str, int] = defaultdict(int)

    all_ranks = []
    all_relevant_counts = [0] * len(cutoffs)
    total_queries_with_results = 0

    for case in normalized_cases:
        retrieved = search_fn(
            query=case["query"],
            course_slug=course_slug,
            topic_slug=None,
            limit=max_k,
        )

        if not isinstance(retrieved, list):
            raise TypeError(
                f"Retrieval for golden case {case['id']} "
                "must return a list."
            )

        relevant_flags = []
        retrieved_topic_slugs = []

        for position, chunk in enumerate(retrieved[:max_k], start=1):
            if not isinstance(chunk, Mapping):
                raise TypeError(
                    f"Retrieved item {position} for golden case "
                    f"{case['id']} must be a mapping."
                )

            topic_slug = chunk.get("topic_slug")
            if topic_slug is not None and not isinstance(topic_slug, str):
                raise TypeError(
                    f"Retrieved item {position} for golden case "
                    f"{case['id']} has an invalid topic_slug."
                )

            retrieved_topic_slugs.append(topic_slug)
            relevant_flags.append(
                topic_slug == case["expected_topic_slug"]
            )

        first_relevant_rank = next(
            (
                rank
                for rank, is_relevant in enumerate(
                    relevant_flags,
                    start=1,
                )
                if is_relevant
            ),
            None,
        )

        if retrieved:
            total_queries_with_results += 1
            topic_retrieved_counts[case["expected_topic_slug"]] += 1

        per_cutoff_relevant = [
            sum(relevant_flags[:cutoff])
            for cutoff in cutoffs
        ]

        case_result = {
            "id": case["id"],
            "expected_topic_slug": case["expected_topic_slug"],
            "first_relevant_rank": first_relevant_rank,
            "retrieved_topic_slugs": retrieved_topic_slugs,
            "hit_at_k": {
                str(cutoff): (
                    first_relevant_rank is not None
                    and first_relevant_rank <= cutoff
                )
                for cutoff in cutoffs
            },
        }
        case_results.append(case_result)

        all_ranks.append(first_relevant_rank)
        for index, relevant_count in enumerate(per_cutoff_relevant):
            all_relevant_counts[index] += relevant_count

        topic_ranks[case["expected_topic_slug"]].append(
            first_relevant_rank
        )
        for index, relevant_count in enumerate(per_cutoff_relevant):
            topic_relevant_counts[case["expected_topic_slug"]][index] += (
                relevant_count
            )

    overall_metrics = _calculate_metrics(
        first_relevant_ranks=all_ranks,
        relevant_counts_at_k=all_relevant_counts,
        cutoffs=cutoffs,
        retrieved_count=total_queries_with_results,
    )

    per_topic = {}
    for topic_slug in sorted(topic_ranks):
        per_topic[topic_slug] = _calculate_metrics(
            first_relevant_ranks=topic_ranks[topic_slug],
            relevant_counts_at_k=topic_relevant_counts[topic_slug],
            cutoffs=cutoffs,
            retrieved_count=topic_retrieved_counts[topic_slug],
        )

    return {
        "course_slug": course_slug,
        "top_k": max_k,
        "evaluation_cutoffs": list(cutoffs),
        **overall_metrics,
        "per_topic": per_topic,
        "cases": case_results,
    }
