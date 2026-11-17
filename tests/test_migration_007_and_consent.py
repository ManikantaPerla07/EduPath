"""Isolated tests for Migration 007 Schema, Consent Enforcement, and Account Deletion.

Verifies:
1. Migration 007 DDL structure, column consistency, defaults, and cascade semantics.
2. Application behavior under Condition A (Migration 007 not applied) vs Condition B (Applied).
3. Zero Gemini API calls when AI consent is denied or absent.
4. Account deletion across multiple chat threads, zero threads, checkpoint failures, and retries.
"""

import re
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from uuid import UUID, uuid4

from agents.tutor_graph import run_tutor_graph
from services.learner_service import (
    get_learner_profile,
    set_ai_consent,
    complete_onboarding,
    delete_learner_account,
)
from services.misconception_service import (
    record_learner_misconceptions,
    fetch_active_learner_misconceptions,
    resolve_learner_misconception,
    diagnose_student_misconceptions,
)
from services.subjective_evaluation_service import (
    evaluate_subjective_explanation,
    evaluate_subjective_explanation_deterministic,
)


class Migration007SchemaTests(unittest.TestCase):
    """Test 1: Migration 007 Schema Consistency and DDL Integrity."""

    @classmethod
    def setUpClass(cls):
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "database"
            / "migrations"
            / "007_learner_profile_and_misconceptions.sql"
        )
        cls.sql_content = migration_path.read_text(encoding="utf-8")

    def test_migration_file_exists_and_is_non_empty(self):
        self.assertTrue(len(self.sql_content) > 100)

    def test_schema_modifications_on_learner_profiles(self):
        sql = self.sql_content.upper()
        # Verify columns added with IF NOT EXISTS
        self.assertIn("ALTER TABLE LEARNER_PROFILES", sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS LEARNING_GOAL TEXT", sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS ONBOARDING_COMPLETED BOOLEAN NOT NULL DEFAULT FALSE", sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS AI_CONSENT BOOLEAN NOT NULL DEFAULT FALSE", sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS AI_CONSENT_GRANTED_AT TIMESTAMPTZ DEFAULT NULL", sql)

    def test_adult_confirmation_preserved_without_redundancy(self):
        sql = self.sql_content.lower()
        # Confirms no redundant adult_confirmed or redefinition of adult_confirmation
        self.assertNotIn("add column if not exists adult_confirmed", sql)
        self.assertNotIn("add column adult_confirmed", sql)
        self.assertIn("adult_confirmation was established in 001_initial_schema.sql", sql)

    def test_learner_misconceptions_table_schema(self):
        sql = self.sql_content.lower()
        self.assertIn("create table if not exists learner_misconceptions", sql)
        # Check required columns
        self.assertIn("misconception_record_id uuid primary key default gen_random_uuid()", sql)
        self.assertIn("user_id uuid not null references users(user_id) on delete cascade", sql)
        self.assertIn("misconception_code varchar(100) not null", sql)
        self.assertIn("topic_slug varchar(100) not null", sql)
        self.assertIn("short_description text not null", sql)
        self.assertIn("corrective_explanation text not null", sql)
        self.assertIn("detection_method varchar(50) not null default 'rule_based'", sql)
        self.assertIn("confidence_score numeric(3, 2) not null default 1.00", sql)
        self.assertIn("is_active boolean not null default true", sql)
        self.assertIn("diagnosed_at timestamptz not null default now()", sql)
        self.assertIn("detected_at timestamptz not null default now()", sql)
        self.assertIn("resolved_at timestamptz default null", sql)

    def test_indexes_on_learner_misconceptions(self):
        sql = self.sql_content.lower()
        self.assertIn("create index if not exists idx_learner_misconceptions_user_topic", sql)
        self.assertIn("on learner_misconceptions(user_id, topic_slug, is_active)", sql)
        self.assertIn("create index if not exists idx_learner_misconceptions_code", sql)
        self.assertIn("on learner_misconceptions(misconception_code)", sql)


class ConditionAPreMigrationTests(unittest.TestCase):
    """Test 2A: Application behavior when Migration 007 has NOT been applied."""

    def setUp(self):
        self.user_id = uuid4()

    def test_profile_defaults_ai_consent_false_when_columns_missing(self):
        """When 007 columns do not exist in the database, consent defaults to False and onboarding to False."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        # Base query returns user and initial profile
        base_row = (
            self.user_id, "student@test.com", "Test Student", "student", True,
            False, "beginner", "English", "step_by_step", 45, "Master Python",
        )
        cursor.fetchone.return_value = base_row
        # information_schema query returns empty list (no 007 columns)
        cursor.fetchall.return_value = []

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ):
            profile = get_learner_profile(str(self.user_id))

        self.assertFalse(profile["ai_consent"])
        self.assertIsNone(profile["ai_consent_granted_at"])
        self.assertFalse(profile["onboarding_completed"])
        self.assertFalse(profile["adult_confirmation"])
        self.assertEqual(profile["learning_goal"], "Master Python")

    def test_set_ai_consent_is_safe_when_column_missing(self):
        """Attempting to update consent before migration does not crash or execute bad SQL."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        # information_schema returns no ai_consent column
        cursor.fetchall.return_value = []

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ):
            # Should not raise exception
            set_ai_consent(str(self.user_id), True)
            # UPDATE query should NOT have been executed
            self.assertEqual(cursor.execute.call_count, 1)  # only the SELECT column check

    def test_misconception_service_fails_safely_when_table_missing(self):
        """When learner_misconceptions table is absent, recording and fetching return empty lists."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        # Table does not exist
        cursor.fetchone.return_value = (False,)

        with patch("services.misconception_service.psycopg.connect", return_value=connection), patch(
            "services.misconception_service.load_database_url", return_value="postgresql://test"
        ):
            diagnoses = diagnose_student_misconceptions("range(1, 5) includes 5")
            rec = record_learner_misconceptions(str(self.user_id), diagnoses)
            self.assertEqual(rec, [])

            active = fetch_active_learner_misconceptions(str(self.user_id))
            self.assertEqual(active, [])

            resolved = resolve_learner_misconception(str(self.user_id), "off_by_one_range")
            self.assertFalse(resolved)


class ConditionBPostMigrationTests(unittest.TestCase):
    """Test 2B: Application behavior when Migration 007 IS applied."""

    def setUp(self):
        self.user_id = uuid4()

    def test_consent_persistence_and_timestamping(self):
        """When migration is applied, granting consent persists True and records timestamp."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchall.return_value = [("ai_consent",), ("ai_consent_granted_at",)]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ):
            set_ai_consent(str(self.user_id), True)
            self.assertEqual(cursor.execute.call_count, 2)
            update_sql = cursor.execute.call_args_list[1].args[0]
            self.assertIn("ai_consent = %s", update_sql)
            self.assertIn("ai_consent_granted_at = CASE WHEN %s THEN NOW() ELSE NULL END", update_sql)
            params = cursor.execute.call_args_list[1].args[1]
            self.assertEqual(params, (True, True, self.user_id))

    def test_consent_revocation_clears_timestamp(self):
        """Revoking consent sets ai_consent = False and clears granted timestamp."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchall.return_value = [("ai_consent",), ("ai_consent_granted_at",)]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ):
            set_ai_consent(str(self.user_id), False)
            params = cursor.execute.call_args_list[1].args[1]
            self.assertEqual(params, (False, False, self.user_id))

    def test_misconception_persistence_and_learner_isolation(self):
        """Misconceptions are saved with user_id, topic_slug, diagnosed_at and queried by user."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        record_id = uuid4()
        # 1. table exists: (True,)
        # 2. insert returns record_id
        cursor.fetchone.side_effect = [(True,), (record_id,)]

        diagnoses = [{
            "misconception_code": "off_by_one_range",
            "topic": "Loops",
            "topic_slug": "loops",
            "short_description": "Exclusive upper bound error",
            "corrective_explanation": "range(1, 5) stops at 4",
            "confidence": 0.95,
            "detection_method": "catalogue_rule_based",
        }]

        with patch("services.misconception_service.psycopg.connect", return_value=connection), patch(
            "services.misconception_service.load_database_url", return_value="postgresql://test"
        ):
            rec_ids = record_learner_misconceptions(str(self.user_id), diagnoses)
            self.assertEqual(rec_ids, [str(record_id)])
            insert_query = cursor.execute.call_args_list[1].args[0]
            self.assertIn("INSERT INTO learner_misconceptions", insert_query)
            self.assertIn("user_id", insert_query)


class GeminiConsentEnforcementTests(unittest.TestCase):
    """Test 3: Strict zero-call Gemini enforcement when consent is denied or absent."""

    def setUp(self):
        self.user_id = str(uuid4())
        self.thread_id = str(uuid4())

    def test_tutor_graph_raises_permission_error_when_consent_denied(self):
        """run_tutor_graph must raise PermissionError immediately when ai_consent is False in DB."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "agents.tutor_graph.open_langgraph_checkpointer"
        ) as mock_cp, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": False, "adult_confirmation": True},
        ):
            with self.assertRaises(PermissionError) as ctx:
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    session_id=self.thread_id,
                    ai_consent=False,
                    adult_confirmation=True,
                )
            self.assertIn("affirmative consent", str(ctx.exception).lower())
            mock_build.assert_not_called()
            mock_cp.assert_not_called()

    def test_tutor_graph_raises_permission_error_when_consent_is_none(self):
        """run_tutor_graph must raise PermissionError immediately when ai_consent is None in DB."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": None, "adult_confirmation": True},
        ):
            with self.assertRaises(PermissionError) as ctx:
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    session_id=self.thread_id,
                    ai_consent=None,
                    adult_confirmation=True,
                )
            self.assertIn("affirmative consent", str(ctx.exception).lower())
            mock_build.assert_not_called()

    def test_tutor_graph_raises_permission_error_when_consent_is_missing(self):
        """run_tutor_graph must raise PermissionError immediately when ai_consent is omitted in DB."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            return_value={"adult_confirmation": True},
        ):
            with self.assertRaises(PermissionError) as ctx:
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    session_id=self.thread_id,
                    adult_confirmation=True,
                )
            self.assertIn("affirmative consent", str(ctx.exception).lower())
            mock_build.assert_not_called()

    def test_tutor_graph_raises_permission_error_when_adult_confirmation_denied(self):
        """run_tutor_graph must raise PermissionError immediately when adult_confirmation is False in DB."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True, "adult_confirmation": False},
        ):
            with self.assertRaises(PermissionError) as ctx:
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    session_id=self.thread_id,
                    ai_consent=True,
                    adult_confirmation=False,
                )
            self.assertIn("adult", str(ctx.exception).lower())
            mock_build.assert_not_called()

    def test_tutor_graph_raises_permission_error_when_adult_confirmation_is_none(self):
        """run_tutor_graph must raise PermissionError immediately when adult_confirmation is None in DB."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True, "adult_confirmation": None},
        ):
            with self.assertRaises(PermissionError) as ctx:
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    session_id=self.thread_id,
                    ai_consent=True,
                    adult_confirmation=None,
                )
            self.assertIn("adult", str(ctx.exception).lower())
            mock_build.assert_not_called()

    def test_tutor_graph_raises_permission_error_when_adult_confirmation_is_missing(self):
        """run_tutor_graph must raise PermissionError immediately when adult_confirmation is omitted in DB."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True},
        ):
            with self.assertRaises(PermissionError) as ctx:
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    session_id=self.thread_id,
                    ai_consent=True,
                )
            self.assertIn("adult", str(ctx.exception).lower())
            mock_build.assert_not_called()

    def test_subjective_evaluation_routes_to_deterministic_when_consent_denied(self):
        """evaluate_subjective_explanation must not call Gemini when ai_consent is False in DB."""
        with patch(
            "services.subjective_evaluation_service.evaluate_subjective_explanation_gemini"
        ) as mock_gemini, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": False, "adult_confirmation": True},
        ):
            result = evaluate_subjective_explanation(
                question="Why is range(1, 5) stopping at 4?",
                reference_answer="In Python range(start, stop) the stop value is exclusive.",
                student_explanation="range(1, 5) generates 1, 2, 3, 4, but not 5.",
                topic_slug="loops",
                user_id=self.user_id,
                ai_consent=False,
                adult_confirmation=True,
                use_ai=True,
            )
            mock_gemini.assert_not_called()
            self.assertEqual(result["evaluator_type"], "deterministic_fallback")
            self.assertIn("consent", result.get("fallback_reason", "").lower())
            self.assertGreater(result["score_percent"], 0)
            self.assertIn("rubric_breakdown", result)

    def test_subjective_evaluation_routes_to_deterministic_when_consent_none(self):
        """evaluate_subjective_explanation must not call Gemini when ai_consent is None in DB."""
        with patch(
            "services.subjective_evaluation_service.evaluate_subjective_explanation_gemini"
        ) as mock_gemini, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": None, "adult_confirmation": True},
        ):
            result = evaluate_subjective_explanation(
                question="Why is range(1, 5) stopping at 4?",
                reference_answer="In Python range(start, stop) the stop value is exclusive.",
                student_explanation="range(1, 5) generates 1, 2, 3, 4, but not 5.",
                topic_slug="loops",
                user_id=self.user_id,
                ai_consent=None,
                adult_confirmation=True,
                use_ai=True,
            )
            mock_gemini.assert_not_called()
            self.assertEqual(result["evaluator_type"], "deterministic_fallback")
            self.assertIn("consent", result.get("fallback_reason", "").lower())

    def test_subjective_evaluation_routes_to_deterministic_when_adult_confirmation_denied(self):
        """evaluate_subjective_explanation must not call Gemini when adult_confirmation is False in DB."""
        with patch(
            "services.subjective_evaluation_service.evaluate_subjective_explanation_gemini"
        ) as mock_gemini, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True, "adult_confirmation": False},
        ):
            result = evaluate_subjective_explanation(
                question="Why is range(1, 5) stopping at 4?",
                reference_answer="In Python range(start, stop) the stop value is exclusive.",
                student_explanation="range(1, 5) generates 1, 2, 3, 4, but not 5.",
                topic_slug="loops",
                user_id=self.user_id,
                ai_consent=True,
                adult_confirmation=False,
                use_ai=True,
            )
            mock_gemini.assert_not_called()
            self.assertEqual(result["evaluator_type"], "deterministic_fallback")
            self.assertIn("adult", result.get("fallback_reason", "").lower())

    def test_tutor_graph_blocks_when_user_id_missing(self):
        """Missing user_id must immediately block tutor graph and raise PermissionError."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build:
            with self.assertRaises(PermissionError):
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=None,
                )
            mock_build.assert_not_called()

    def test_tutor_graph_blocks_when_db_consent_false_even_if_supplied_true(self):
        """Database consent=False, supplied consent=True: BLOCK."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": False, "adult_confirmation": True},
        ):
            with self.assertRaises(PermissionError):
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    ai_consent=True,
                )
            mock_build.assert_not_called()

    def test_tutor_graph_uses_authoritative_db_consent_true_when_supplied_false(self):
        """Database consent=True, supplied consent=False: use authoritative DB state."""
        expected_result = {
            "answer": "Range explanation [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "gemini-3.8-flash",
            "reason": None,
        }
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"answer_result": expected_result}
        with patch("agents.tutor_graph.build_tutor_graph", return_value=mock_graph), patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True, "adult_confirmation": True},
        ):
            res = run_tutor_graph(
                question="How does range work?",
                course_slug="python-basics",
                user_id=self.user_id,
                ai_consent=False,
            )
            self.assertEqual(res, expected_result)
            mock_graph.invoke.assert_called_once()

    def test_tutor_graph_blocks_when_db_adult_confirmation_false_even_if_supplied_true(self):
        """Database adult_confirmation=False, supplied value=True: BLOCK."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True, "adult_confirmation": False},
        ):
            with self.assertRaises(PermissionError):
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    adult_confirmation=True,
                )
            mock_build.assert_not_called()

    def test_tutor_graph_blocks_when_db_lookup_fails(self):
        """Database lookup exception: BLOCK."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            side_effect=RuntimeError("Neon connection terminated"),
        ):
            with self.assertRaises(PermissionError) as ctx:
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                )
            self.assertIn("could not be verified", str(ctx.exception).lower())
            mock_build.assert_not_called()

    def test_tutor_graph_blocks_when_consent_revoked_in_db_despite_old_session(self):
        """Consent revoked in PostgreSQL while an old session contains True: BLOCK."""
        with patch("agents.tutor_graph.build_tutor_graph") as mock_build, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": False, "adult_confirmation": True},
        ):
            with self.assertRaises(PermissionError):
                run_tutor_graph(
                    question="How does range work?",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    session_id=self.thread_id,
                    ai_consent=True,
                )
            mock_build.assert_not_called()

    def test_tutor_graph_proceeds_when_db_consent_and_adult_true(self):
        """Consent=True and adult_confirmation=True in PostgreSQL: AI workflow can proceed."""
        expected_result = {
            "answer": "Grounded answer [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "gemini-3.8-flash",
            "reason": None,
        }
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"answer_result": expected_result}
        with patch("agents.tutor_graph.build_tutor_graph", return_value=mock_graph), patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": True, "adult_confirmation": True},
        ):
            res = run_tutor_graph(
                question="How does range work?",
                course_slug="python-basics",
                user_id=self.user_id,
            )
            self.assertEqual(res, expected_result)
            mock_graph.invoke.assert_called_once()

    def test_deterministic_evaluation_runs_without_consent_or_credentials(self):
        """Deterministic evaluation has zero dependency on AI consent or Gemini API keys."""
        result = evaluate_subjective_explanation_deterministic(
            question="Why can't you change a character in a string directly?",
            reference_answer="Python strings are immutable. Slicing must be used instead.",
            student_explanation="Python strings are immutable objects so in-place modification is forbidden. Slicing must be used to create a new string instead.",
            topic_slug="variables",
        )
        self.assertEqual(result["evaluator_type"], "deterministic_fallback")
        self.assertGreaterEqual(result["score_percent"], 50.0)
        self.assertIn("conceptual_accuracy", result["rubric_breakdown"])
        self.assertIn("reasoning_and_logic", result["rubric_breakdown"])
        self.assertIn("edge_cases_and_gotchas", result["rubric_breakdown"])
        self.assertIn("clarity_of_expression", result["rubric_breakdown"])


class AccountDeletionAndLangGraphCleanupTests(unittest.TestCase):
    """Test 5: Account deletion edge cases, multi-connection semantics, and idempotency."""

    def setUp(self):
        self.user_id = uuid4()
        self.thread_1 = str(uuid4())
        self.thread_2 = str(uuid4())

    def test_delete_account_with_multiple_chat_threads(self):
        """Account deletion with multiple threads cleans up all thread checkpoints."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        # 1. user exists (SELECT FOR UPDATE)
        # 2. table exists check for learner_misconceptions
        # 3. delete users returns user_id
        cursor.fetchone.side_effect = [
            (self.user_id, True),
            (True,),
            (self.user_id,),
        ]
        # fetchall for thread_ids
        cursor.fetchall.side_effect = [
            [(self.thread_1,), (self.thread_2,)],
        ]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ), patch(
            "services.langgraph_checkpoint_service.delete_langgraph_thread_checkpoints"
        ) as mock_delete_cp:
            success = delete_learner_account(str(self.user_id))
            self.assertTrue(success)
            self.assertEqual(mock_delete_cp.call_count, 2)
            mock_delete_cp.assert_any_call(thread_id=self.thread_1, database_url="postgresql://test")
            mock_delete_cp.assert_any_call(thread_id=self.thread_2, database_url="postgresql://test")

    def test_delete_account_with_zero_chat_threads(self):
        """Account deletion with zero threads succeeds cleanly without invoking checkpoint cleanup."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchone.side_effect = [
            (self.user_id, True),
            (True,),
            (self.user_id,),
        ]
        cursor.fetchall.side_effect = [
            [],  # No chat sessions
        ]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ), patch(
            "services.langgraph_checkpoint_service.delete_langgraph_thread_checkpoints"
        ) as mock_delete_cp:
            success = delete_learner_account(str(self.user_id))
            self.assertTrue(success)
            mock_delete_cp.assert_not_called()

    def test_checkpoint_failure_aborts_relational_deletion(self):
        """If checkpoint deletion fails for any thread, the transaction aborts and users row is preserved."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchone.side_effect = [(self.user_id, True)]
        cursor.fetchall.side_effect = [[(self.thread_1,)]]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ), patch(
            "services.langgraph_checkpoint_service.delete_langgraph_thread_checkpoints",
            side_effect=RuntimeError("LangGraph checkpointer network failure"),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                delete_learner_account(str(self.user_id))
            self.assertIn("Failed to delete LangGraph checkpoints", str(ctx.exception))
            # Verify DELETE FROM users was NEVER called
            executed_sql = [call_item.args[0] for call_item in cursor.execute.call_args_list]
            self.assertFalse(any("DELETE FROM users" in sql for sql in executed_sql))

    def test_retry_of_incomplete_deletion_is_idempotent(self):
        """If relational deletion fails after checkpoints deleted, retry cleans up without error."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        # Simulate second run (retry) where user still exists and chat_sessions still returned
        cursor.fetchone.side_effect = [
            (self.user_id, True),
            (True,),
            (self.user_id,),
        ]
        cursor.fetchall.side_effect = [
            [(self.thread_1,)],
        ]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ), patch(
            "services.langgraph_checkpoint_service.delete_langgraph_thread_checkpoints"
        ) as mock_delete_cp:
            # Checkpoint deletion succeeds (it's idempotent in SQL: DELETE WHERE thread_id=...)
            success = delete_learner_account(str(self.user_id))
            self.assertTrue(success)
            mock_delete_cp.assert_called_once_with(
                thread_id=self.thread_1, database_url="postgresql://test"
            )

    def test_attempted_deletion_of_nonexistent_learner_returns_false(self):
        """Attempting to delete a non-existent learner returns False without executing deletes."""
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchone.return_value = None  # user not found

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ), patch(
            "services.langgraph_checkpoint_service.delete_langgraph_thread_checkpoints"
        ) as mock_delete_cp:
            success = delete_learner_account(str(self.user_id))
            self.assertFalse(success)
            mock_delete_cp.assert_not_called()
            # No DELETE queries executed
            executed_sql = [call_item.args[0] for call_item in cursor.execute.call_args_list]
            self.assertFalse(any("DELETE" in sql for sql in executed_sql))


class LearnerConsentLifecycleTests(unittest.TestCase):
    """Test 6: Full Application-Layer Consent Lifecycle.
    - New learner starts with consent false.
    - Learner grants consent and it persists in PostgreSQL.
    - Logout/re-login retains the state.
    - Revoking consent updates persistence to false.
    - Revocation strictly blocks all LLM providers (Gemini & Groq).
    """

    def setUp(self):
        self.user_id = str(uuid4())

    def test_new_learner_starts_with_consent_false(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchall.return_value = [("ai_consent",), ("ai_consent_granted_at",), ("onboarding_completed",)]
        base_row = (
            str(self.user_id), "test@example.com", "Test Learner", "student", True,
            True, "beginner", "English", "step_by_step", 45, "Master Python"
        )
        ext_row = (False, None, False)
        cursor.fetchone.side_effect = [base_row, ext_row]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ):
            profile = get_learner_profile(self.user_id)
            self.assertFalse(profile["ai_consent"])
            self.assertFalse(profile["onboarding_completed"])

    def test_granting_consent_persists_in_postgres(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchall.return_value = [("ai_consent",), ("ai_consent_granted_at",)]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ):
            set_ai_consent(self.user_id, True)
            update_sql = cursor.execute.call_args_list[1].args[0]
            params = cursor.execute.call_args_list[1].args[1]
            self.assertIn("ai_consent = %s", update_sql)
            self.assertEqual(params[0], True)

    def test_logout_and_relogin_retains_granted_consent(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchall.return_value = [("ai_consent",), ("ai_consent_granted_at",), ("onboarding_completed",)]
        base_row = (
            str(self.user_id), "test@example.com", "Test Learner", "student", True,
            True, "beginner", "English", "step_by_step", 45, "Master Python"
        )
        ext_row = (True, "2026-11-14T10:00:00Z", True)
        cursor.fetchone.side_effect = [base_row, ext_row]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ):
            reloaded_profile = get_learner_profile(self.user_id)
            self.assertTrue(reloaded_profile["ai_consent"])
            self.assertTrue(reloaded_profile["onboarding_completed"])

    def test_revoking_consent_persists_false_and_blocks_all_providers(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchall.return_value = [("ai_consent",), ("ai_consent_granted_at",)]

        with patch("services.learner_service.psycopg.connect", return_value=connection), patch(
            "services.learner_service.load_database_url", return_value="postgresql://test"
        ):
            set_ai_consent(self.user_id, False)
            params = cursor.execute.call_args_list[1].args[1]
            self.assertEqual(params[0], False)

        with patch("services.llm_provider_service.generate_with_provider_failover") as mock_failover, patch(
            "agents.tutor_graph.build_tutor_graph"
        ) as mock_graph, patch(
            "services.learner_service.get_learner_profile",
            return_value={"ai_consent": False, "adult_confirmation": True},
        ):
            with self.assertRaises(PermissionError):
                run_tutor_graph(
                    question="Explain while loops",
                    course_slug="python-basics",
                    user_id=self.user_id,
                    ai_consent=False,
                )
            mock_failover.assert_not_called()
            mock_graph.assert_not_called()


if __name__ == "__main__":
    unittest.main()
