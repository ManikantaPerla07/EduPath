"""Run the EduPath golden-query RAG retrieval evaluation."""

import argparse
import json
from pathlib import Path
import sys

from services.retrieval_evaluation_service import (
    DEFAULT_EVALUATION_KS,
    evaluate_retrieval_cases,
)
from services.retrieval_service import search_knowledge_base


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_QUERIES_FILE = (
    PROJECT_ROOT / "evaluation" / "retrieval_golden_queries.json"
)


def _load_golden_queries() -> list[dict]:
    """Load the checked-in, topic-aligned query benchmark."""

    try:
        cases = json.loads(
            GOLDEN_QUERIES_FILE.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Could not read the RAG golden-query dataset."
        ) from exc

    if not isinstance(cases, list):
        raise RuntimeError(
            "The RAG golden-query dataset must contain a JSON array."
        )

    return cases


def _print_report(report: dict) -> None:
    """Print a compact human-readable retrieval report."""

    print("\n========== EDUPATH RAG RETRIEVAL EVALUATION ==========")
    print("Course                 :", report["course_slug"])
    print("Golden queries         :", report["query_count"])
    print(
        "Queries with results   :",
        f"{report['queries_with_results']}/{report['query_count']}",
    )
    print(
        "Retrieval coverage     :",
        f"{report['retrieval_coverage_percent']:.1f}%",
    )
    print(
        "Mean reciprocal rank  :",
        f"{report['mean_reciprocal_rank']:.3f}",
    )

    print("\nRanking metrics:")
    print("| Cutoff | Hit@K | Precision@K |")
    print("|---:|---:|---:|")
    for cutoff in report["evaluation_cutoffs"]:
        key = str(cutoff)
        hit_rate = report["hit_rate_at_k"][key] * 100
        precision = report["precision_at_k"][key] * 100
        print(
            f"| {cutoff} | {hit_rate:.1f}% | {precision:.1f}% |"
        )

    print("\nPer-topic Hit@K:")
    max_k = str(report["top_k"])
    for topic_slug, metrics in report["per_topic"].items():
        hit_rate = metrics["hit_rate_at_k"][max_k] * 100
        print(
            f"- {topic_slug}: {hit_rate:.1f}% "
            f"({metrics['queries_with_results']}/"
            f"{metrics['query_count']} queries with results)"
        )

    misses = [
        case
        for case in report["cases"]
        if case["first_relevant_rank"] is None
    ]

    print("\nQueries without a matching topic in the retrieved results:")
    if not misses:
        print("- None")
    else:
        for case in misses:
            found_topics = [
                slug if slug else "(course-wide resource)"
                for slug in case["retrieved_topic_slugs"]
            ]
            print(
                f"- {case['id']} expected={case['expected_topic_slug']} "
                f"retrieved={found_topics or 'no results'}"
            )

    print(
        "\nNote: these metrics measure topic-level retrieval alignment. "
        "They do not establish factual correctness or answer quality."
    )


def main(argv: list[str] | None = None) -> int:
    """Run evaluation and optionally write a JSON report."""

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate EduPath course-wide RAG retrieval against "
            "the checked-in topic-aligned golden queries."
        )
    )
    parser.add_argument(
        "--course-slug",
        default="python-basics",
        help="Course slug to evaluate (default: python-basics).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Optional JSON output path, for example "
            "retrieval-evaluation.json."
        ),
    )
    args = parser.parse_args(argv)

    try:
        report = evaluate_retrieval_cases(
            cases=_load_golden_queries(),
            search_fn=search_knowledge_base,
            course_slug=args.course_slug,
            ks=DEFAULT_EVALUATION_KS,
        )
    except Exception as exc:
        print(
            "RAG retrieval evaluation failed:",
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    _print_report(report)

    if args.output is not None:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            print(
                f"Could not write evaluation report: {exc}",
                file=sys.stderr,
            )
            return 1

        print(f"\nJSON report saved to: {args.output}")

    if report["queries_with_results"] == 0:
        print(
            "\nNo retrieval results were found. Confirm that the course "
            "is published and its topic resources are fully embedded.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
