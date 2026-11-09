import pytest
from unittest.mock import patch

from services.adaptive_assessment_service import (
    normalize_adaptive_answer,
    submit_adaptive_answer,
)


class TestAdaptiveAnswerValidation:

    @pytest.mark.parametrize(
        "answer, expected",
        [
            ("A", "A"),
            ("b", "B"),
            (" C ", "C"),
            ("d", "D"),
        ],
    )
    def test_normalizes_answer_letters(self, answer, expected):
        assert normalize_adaptive_answer(answer) == expected

    @pytest.mark.parametrize(
        "answer",
        ["", " ", "E", "AB", None, 1, True, [], {}],
    )
    def test_rejects_invalid_answers(self, answer):
        with pytest.raises(ValueError):
            normalize_adaptive_answer(answer)

    def test_invalid_user_id_does_not_access_database(self):
        with patch(
            "services.adaptive_assessment_service.psycopg.connect"
        ) as database:
            with pytest.raises(ValueError, match="learner"):
                submit_adaptive_answer(
                    user_id="invalid-user",
                    assessment_id="123e4567-e89b-12d3-a456-426614174000",
                    item_id="123e4567-e89b-12d3-a456-426614174001",
                    answer="A",
                )

        database.assert_not_called()

    def test_invalid_assessment_id_does_not_access_database(self):
        with patch(
            "services.adaptive_assessment_service.psycopg.connect"
        ) as database:
            with pytest.raises(ValueError, match="assessment"):
                submit_adaptive_answer(
                    user_id="123e4567-e89b-12d3-a456-426614174000",
                    assessment_id="invalid-assessment",
                    item_id="123e4567-e89b-12d3-a456-426614174001",
                    answer="A",
                )

        database.assert_not_called()

    def test_invalid_item_id_does_not_access_database(self):
        with patch(
            "services.adaptive_assessment_service.psycopg.connect"
        ) as database:
            with pytest.raises(ValueError, match="item"):
                submit_adaptive_answer(
                    user_id="123e4567-e89b-12d3-a456-426614174000",
                    assessment_id="123e4567-e89b-12d3-a456-426614174001",
                    item_id="invalid-item",
                    answer="A",
                )

        database.assert_not_called()

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.adaptive_assessment_service import submit_adaptive_answer


class TestAdaptiveAnswerSubmission:

    def setup_method(self):
        self.user_id = uuid4()
        self.assessment_id = uuid4()
        self.course_id = uuid4()
        self.item_id = uuid4()
        self.question_bank_id = uuid4()
        self.topic_id = uuid4()
        self.response_id = uuid4()
        self.next_item_id = uuid4()

        self.session_row = (
            self.assessment_id,
            "in_progress",
            "practice",
            self.course_id,
            "python-basics",
        )

        self.question_row = (
            self.question_bank_id,
            self.topic_id,
            "Which keyword defines a variable?",
            ["A. =", "B. def", "C. class", "D. import"],
            "A",
            "The assignment operator is used to assign a value.",
            "easy",
            Decimal("1"),
            "variables",
        )

        self.next_question = {
            "question_id": uuid4(),
            "question_code": "VAR-M",
            "question_type": "mcq",
            "question_text": "Which statement updates a variable?",
            "options": [
                "A. x == 2",
                "B. x = 2",
                "C. x != 2",
                "D. x >= 2",
            ],
            "correct_answer": "B",
            "explanation": "The assignment operator is =.",
            "difficulty": "medium",
            "topic_id": uuid4(),
            "topic_slug": "variables",
            "topic_name": "Variables",
            "sequence_number": 1,
        }

    def make_database(self, fetchone_results):
        connection = MagicMock()
        cursor = MagicMock()

        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.side_effect = fetchone_results

        return connection, cursor

    def call_service(self, connection):
        with (
            patch(
                "services.adaptive_assessment_service.psycopg.connect",
                return_value=connection,
            ),
            patch(
                "services.adaptive_assessment_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.adaptive_assessment_service._load_topic_progress",
                return_value=[
                    {
                        "topic_slug": "variables",
                        "mastery_status": "developing",
                        "sequence_order": 1,
                    }
                ],
            ),
            patch(
                "services.adaptive_assessment_service._load_question_candidates",
                return_value=[self.next_question],
            ),
            patch(
                "services.adaptive_assessment_service._load_used_question_ids",
                return_value={str(self.question_bank_id)},
            ),
            patch(
                "services.adaptive_assessment_service._load_recent_question_ids",
                return_value=set(),
            ),
            patch(
                "services.adaptive_assessment_service.select_next_adaptive_question",
                return_value=self.next_question,
            ) as select_next,
        ):
            result = submit_adaptive_answer(
                user_id=str(self.user_id),
                assessment_id=str(self.assessment_id),
                item_id=str(self.item_id),
                answer="a",
            )

        return result, select_next

    def test_correct_answer_is_saved_and_next_question_is_created(self):
        connection, cursor = self.make_database([
            self.session_row,
            self.question_row,
            (self.response_id,),
            (1,),
            (self.next_item_id,),
        ])

        result, select_next = self.call_service(connection)

        assert result["status"] == "in_progress"
        assert result["answered_questions"] == 1
        assert result["total_questions"] == 5
        assert result["last_answer_feedback"]["is_correct"] is True
        assert result["next_question"]["difficulty"] == "medium"
        assert result["next_question"]["item_id"] == str(self.next_item_id)

        insert_response_calls = [
            call for call in cursor.execute.call_args_list
            if "INSERT INTO assessment_responses" in call.args[0]
        ]
        assert len(insert_response_calls) == 1

        insert_item_calls = [
            call for call in cursor.execute.call_args_list
            if "INSERT INTO assessment_items" in call.args[0]
        ]
        assert len(insert_item_calls) == 1

        select_next.assert_called_once()

    def test_question_must_belong_to_learner_session(self):
        connection, cursor = self.make_database([None])

        with (
            patch(
                "services.adaptive_assessment_service.psycopg.connect",
                return_value=connection,
            ),
            patch(
                "services.adaptive_assessment_service.load_database_url",
                return_value="postgresql://test",
            ),
        ):
            with pytest.raises(PermissionError):
                submit_adaptive_answer(
                    user_id=str(self.user_id),
                    assessment_id=str(self.assessment_id),
                    item_id=str(self.item_id),
                    answer="A",
                )

        assert cursor.execute.call_count == 1

    def test_already_answered_question_is_rejected(self):
        connection, cursor = self.make_database([
            self.session_row,
            None,
        ])

        with (
            patch(
                "services.adaptive_assessment_service.psycopg.connect",
                return_value=connection,
            ),
            patch(
                "services.adaptive_assessment_service.load_database_url",
                return_value="postgresql://test",
            ),
        ):
            with pytest.raises(ValueError, match="not pending"):
                submit_adaptive_answer(
                    user_id=str(self.user_id),
                    assessment_id=str(self.assessment_id),
                    item_id=str(self.item_id),
                    answer="A",
                )

        response_inserts = [
            call for call in cursor.execute.call_args_list
            if "INSERT INTO assessment_responses" in call.args[0]
        ]
        assert len(response_inserts) == 0

    def test_diagnostic_session_cannot_use_incremental_submission(self):
        diagnostic_session = (
            self.assessment_id,
            "in_progress",
            "diagnostic",
            self.course_id,
            "python-basics",
        )

        connection, cursor = self.make_database([diagnostic_session])

        with (
            patch(
                "services.adaptive_assessment_service.psycopg.connect",
                return_value=connection,
            ),
            patch(
                "services.adaptive_assessment_service.load_database_url",
                return_value="postgresql://test",
            ),
        ):
            with pytest.raises(ValueError, match="adaptive assessments"):
                submit_adaptive_answer(
                    user_id=str(self.user_id),
                    assessment_id=str(self.assessment_id),
                    item_id=str(self.item_id),
                    answer="A",
                )

        assert cursor.execute.call_count == 1

    def test_fifth_answer_finalizes_adaptive_assessment(self):
        connection, cursor = self.make_database([
            self.session_row,
            self.question_row,
            (self.response_id,),
            (5,),
        ])

        expected_result = {
            "assessment_id": str(self.assessment_id),
            "status": "submitted",
        }

        with (
            patch(
                "services.adaptive_assessment_service.psycopg.connect",
                return_value=connection,
            ),
            patch(
                "services.adaptive_assessment_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.adaptive_assessment_service._build_adaptive_result",
                return_value=expected_result,
            ) as finalize,
        ):
            result = submit_adaptive_answer(
                user_id=str(self.user_id),
                assessment_id=str(self.assessment_id),
                item_id=str(self.item_id),
                answer="A",
            )

        assert result["status"] == "submitted"
        assert result["last_answer_feedback"]["is_correct"] is True

        finalize.assert_called_once_with(
            cursor,
            self.assessment_id,
            self.user_id,
            "python-basics",
        )
