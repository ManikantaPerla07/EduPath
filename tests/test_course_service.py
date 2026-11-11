"""Tests for course publication and learner access lifecycle services."""

import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from services.course_service import (
    get_admin_course_publication_status,
    is_course_published,
    set_course_publication_status,
)


ADMIN_ID = "11111111-1111-4111-8111-111111111111"
COURSE_ID = UUID("22222222-2222-4222-8222-222222222222")


def make_connection(cursor):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False

    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cursor
    cursor_context.__exit__.return_value = False

    connection.cursor.return_value = cursor_context
    return connection


class CoursePublicationServiceTests(unittest.TestCase):

    def test_admin_can_read_publication_readiness(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ("admin",),
            (COURSE_ID, "Python Programming", False),
            (9,),
            (27,),
            (2,),
        ]
        connection = make_connection(cursor)

        with (
            patch(
                "services.course_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.course_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            result = get_admin_course_publication_status(
                ADMIN_ID,
                "python-basics",
            )

        self.assertEqual(result["topic_count"], 9)
        self.assertEqual(result["active_question_count"], 27)
        self.assertEqual(result["fully_embedded_document_count"], 2)
        self.assertTrue(result["ready_to_publish"])
        self.assertFalse(result["is_published"])

    def test_student_cannot_read_admin_publication_status(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("student",)
        connection = make_connection(cursor)

        with (
            patch(
                "services.course_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.course_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaises(PermissionError):
                get_admin_course_publication_status(
                    ADMIN_ID,
                    "python-basics",
                )

        self.assertEqual(cursor.execute.call_count, 1)

    def test_publishing_requires_topics_questions_and_embedded_resources(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ("admin",),
            (COURSE_ID, False),
            (9,),
            (27,),
            (0,),
        ]
        connection = make_connection(cursor)

        with (
            patch(
                "services.course_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.course_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "fully embedded active learning resource",
            ):
                set_course_publication_status(
                    ADMIN_ID,
                    "python-basics",
                    True,
                )

        self.assertFalse(
            any(
                "UPDATE courses" in call.args[0]
                for call in cursor.execute.call_args_list
            )
        )

    def test_publishing_saves_status_after_readiness_checks(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ("admin",),
            (COURSE_ID, False),
            (9,),
            (27,),
            (1,),
            (True,),
        ]
        connection = make_connection(cursor)

        with (
            patch(
                "services.course_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.course_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            result = set_course_publication_status(
                ADMIN_ID,
                "python-basics",
                True,
            )

        self.assertTrue(result["is_published"])
        self.assertTrue(result["changed"])
        update_calls = [
            call.args
            for call in cursor.execute.call_args_list
            if "UPDATE courses" in call.args[0]
        ]
        self.assertEqual(len(update_calls), 1)
        self.assertEqual(update_calls[0][1], (True, COURSE_ID))

    def test_admin_can_unpublish_without_content_readiness(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ("admin",),
            (COURSE_ID, True),
            (False,),
        ]
        connection = make_connection(cursor)

        with (
            patch(
                "services.course_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.course_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            result = set_course_publication_status(
                ADMIN_ID,
                "python-basics",
                False,
            )

        self.assertFalse(result["is_published"])
        self.assertTrue(result["changed"])

    def test_non_boolean_publication_status_is_rejected_before_database(self):
        with (
            patch("services.course_service.load_database_url") as load_url,
            patch("services.course_service.psycopg.connect") as connect,
        ):
            with self.assertRaises(ValueError):
                set_course_publication_status(
                    ADMIN_ID,
                    "python-basics",
                    "true",
                )

            load_url.assert_not_called()
            connect.assert_not_called()

    def test_publication_lookup_returns_boolean(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (True,)
        connection = make_connection(cursor)

        with (
            patch(
                "services.course_service.load_database_url",
                return_value="postgresql://test",
            ),
            patch(
                "services.course_service.psycopg.connect",
                return_value=connection,
            ),
        ):
            self.assertTrue(is_course_published("python-basics"))


if __name__ == "__main__":
    unittest.main()
