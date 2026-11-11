"""Tests for the topic-aligned RAG retrieval evaluation metrics."""

import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from services.retrieval_evaluation_service import (
    DEFAULT_EVALUATION_KS,
    evaluate_retrieval_cases,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_QUERIES = (
    PROJECT_ROOT / "evaluation" / "retrieval_golden_queries.json"
)


class RetrievalEvaluationFixtureTests(unittest.TestCase):

    def test_golden_dataset_covers_all_nine_course_topics(self):
        cases = json.loads(
            GOLDEN_QUERIES.read_text(encoding="utf-8")
        )

        expected_topics = {
            "variables-data-types",
            "operators",
            "conditionals",
            "loops",
            "functions",
            "lists-tuples",
            "dictionaries-sets",
            "strings",
            "problem-solving",
        }

        self.assertEqual(len(cases), 18)
        self.assertEqual(
            {case["expected_topic_slug"] for case in cases},
            expected_topics,
        )

        topic_counts = {}
        for case in cases:
            topic = case["expected_topic_slug"]
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        self.assertEqual(set(topic_counts.values()), {2})
        self.assertEqual(
            len({case["id"] for case in cases}),
            len(cases),
        )


class RetrievalEvaluationValidationTests(unittest.TestCase):

    def test_rejects_empty_cases(self):
        with self.assertRaises(ValueError):
            evaluate_retrieval_cases([], Mock(), "python-basics")

    def test_rejects_non_mapping_case(self):
        with self.assertRaises(ValueError):
            evaluate_retrieval_cases(
                ["invalid"],
                Mock(),
                "python-basics",
            )

    def test_rejects_missing_golden_case_fields(self):
        for case in (
            {"query": "What is a list?", "expected_topic_slug": "lists-tuples"},
            {"id": "case-1", "expected_topic_slug": "lists-tuples"},
            {"id": "case-1", "query": "What is a list?"},
        ):
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    evaluate_retrieval_cases(
                        [case],
                        Mock(),
                        "python-basics",
                    )

    def test_rejects_duplicate_case_ids(self):
        duplicate_cases = [
            {
                "id": "same",
                "query": "Question one",
                "expected_topic_slug": "operators",
            },
            {
                "id": "same",
                "query": "Question two",
                "expected_topic_slug": "loops",
            },
        ]

        with self.assertRaisesRegex(ValueError, "Duplicate"):
            evaluate_retrieval_cases(
                duplicate_cases,
                Mock(),
                "python-basics",
            )

    def test_rejects_invalid_evaluation_cutoffs(self):
        case = [{
            "id": "case-1",
            "query": "What is a list?",
            "expected_topic_slug": "lists-tuples",
        }]

        for cutoffs in ([], (0,), (21,), (True,), (1.5,), (3, 1), (1, 1)):
            with self.subTest(cutoffs=cutoffs):
                with self.assertRaises(ValueError):
                    evaluate_retrieval_cases(
                        case,
                        Mock(return_value=[]),
                        "python-basics",
                        ks=cutoffs,
                    )

    def test_rejects_empty_course_slug(self):
        with self.assertRaises(ValueError):
            evaluate_retrieval_cases(
                [{
                    "id": "case-1",
                    "query": "What is a list?",
                    "expected_topic_slug": "lists-tuples",
                }],
                Mock(return_value=[]),
                " ",
            )


class RetrievalEvaluationMetricTests(unittest.TestCase):

    def setUp(self):
        self.cases = [
            {
                "id": "variables-01",
                "query": "What is a variable?",
                "expected_topic_slug": "variables-data-types",
            },
            {
                "id": "loops-01",
                "query": "How does break work?",
                "expected_topic_slug": "loops",
            },
            {
                "id": "strings-01",
                "query": "Why are strings immutable?",
                "expected_topic_slug": "strings",
            },
        ]

    def test_calculates_hit_rate_precision_mrr_and_coverage(self):
        ranked_results = {
            "What is a variable?": [
                {"topic_slug": "variables-data-types"},
                {"topic_slug": "operators"},
            ],
            "How does break work?": [
                {"topic_slug": "functions"},
                {"topic_slug": "loops"},
            ],
            "Why are strings immutable?": [
                {"topic_slug": "conditionals"},
                {"topic_slug": None},
            ],
        }

        def search_fn(**kwargs):
            return ranked_results[kwargs["query"]]

        report = evaluate_retrieval_cases(
            self.cases,
            search_fn,
            "python-basics",
            ks=(1, 2),
        )

        self.assertEqual(report["query_count"], 3)
        self.assertEqual(report["queries_with_results"], 3)
        self.assertEqual(report["retrieval_coverage_percent"], 100.0)
        self.assertEqual(report["hit_rate_at_k"]["1"], 1 / 3)
        self.assertEqual(report["hit_rate_at_k"]["2"], 2 / 3)
        self.assertAlmostEqual(
            report["precision_at_k"]["1"],
            1 / 3,
        )
        self.assertAlmostEqual(
            report["precision_at_k"]["2"],
            1 / 3,
        )
        self.assertAlmostEqual(
            report["mean_reciprocal_rank"],
            0.5,
        )

        self.assertEqual(
            report["cases"][1]["first_relevant_rank"],
            2,
        )
        self.assertIsNone(
            report["cases"][2]["first_relevant_rank"]
        )
        self.assertAlmostEqual(
            report["per_topic"]["loops"]["mean_reciprocal_rank"],
            0.5,
        )

    def test_searches_course_wide_without_expected_topic_filter(self):
        search_fn = Mock(return_value=[
            {"topic_slug": "operators"},
        ])

        evaluate_retrieval_cases(
            self.cases[:1],
            search_fn,
            "python-basics",
            ks=(1, 3, 5),
        )

        self.assertEqual(
            search_fn.call_args.kwargs,
            {
                "query": "What is a variable?",
                "course_slug": "python-basics",
                "topic_slug": None,
                "limit": 5,
            },
        )

    def test_counts_empty_retrieval_as_a_miss(self):
        report = evaluate_retrieval_cases(
            self.cases,
            Mock(return_value=[]),
            "python-basics",
        )

        self.assertEqual(report["queries_with_results"], 0)
        self.assertEqual(report["retrieval_coverage_percent"], 0.0)
        self.assertEqual(report["hit_rate_at_k"]["5"], 0.0)
        self.assertEqual(report["mean_reciprocal_rank"], 0.0)
        self.assertTrue(
            all(
                case["first_relevant_rank"] is None
                for case in report["cases"]
            )
        )

    def test_rejects_non_list_retrieval_results(self):
        with self.assertRaises(TypeError):
            evaluate_retrieval_cases(
                self.cases[:1],
                Mock(return_value=None),
                "python-basics",
            )

    def test_rejects_non_mapping_retrieved_chunk(self):
        with self.assertRaises(TypeError):
            evaluate_retrieval_cases(
                self.cases[:1],
                Mock(return_value=["not-a-chunk"]),
                "python-basics",
            )

    def test_rejects_non_string_retrieved_topic_slug(self):
        with self.assertRaises(TypeError):
            evaluate_retrieval_cases(
                self.cases[:1],
                Mock(return_value=[{"topic_slug": 123}]),
                "python-basics",
            )


if __name__ == "__main__":
    unittest.main()
