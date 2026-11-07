import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.learner_service import (
    extract_google_identity,
    get_or_create_learner,
    confirm_adult_status,
)


class LearnerServiceTests(unittest.TestCase):

    def setUp(self):
        self.claims = {
            "iss": "https://accounts.google.com",
            "sub": "google-user-12345",
            "email": "learner@gmail.com",
            "email_verified": True,
            "name": "Test Learner",
        }

    def make_database_mock(self, results, rowcount=1):
        connection = MagicMock()
        cursor = MagicMock()

        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        cursor.fetchone.side_effect = results
        cursor.rowcount = rowcount

        return connection, cursor

    def test_extract_valid_google_identity(self):
        identity = extract_google_identity(self.claims)

        self.assertEqual(identity["subject"], "google-user-12345")
        self.assertEqual(identity["email"], "learner@gmail.com")
        self.assertTrue(identity["email_verified"])

    def test_extract_identity_trims_optional_fields(self):
        claims = {
            **self.claims,
            "email": " learner@gmail.com ",
            "name": " Test Learner ",
        }

        identity = extract_google_identity(claims)

        self.assertEqual(identity["email"], "learner@gmail.com")
        self.assertEqual(identity["display_name"], "Test Learner")

    def test_reject_non_mapping_claims(self):
        with self.assertRaises(ValueError):
            extract_google_identity(None)

    def test_reject_unrecognized_issuer(self):
        claims = {
            **self.claims,
            "iss": "https://untrusted.example.com",
        }

        with self.assertRaises(ValueError):
            extract_google_identity(claims)

    def test_reject_missing_subject(self):
        claims = {**self.claims, "sub": ""}

        with self.assertRaises(ValueError):
            extract_google_identity(claims)

    def test_reject_non_ascii_subject(self):
        claims = {**self.claims, "sub": "learner-你好"}

        with self.assertRaises(ValueError):
            extract_google_identity(claims)

    def test_reject_invalid_email_type(self):
        claims = {**self.claims, "email": 123}

        with self.assertRaises(ValueError):
            extract_google_identity(claims)

    def test_reject_invalid_email_verification_type(self):
        claims = {**self.claims, "email_verified": "true"}

        with self.assertRaises(ValueError):
            extract_google_identity(claims)

    def test_new_learner_and_profile_are_created(self):
        user_id = uuid4()

        user_row = (
            user_id, "student", True,
            "learner@gmail.com", True, "Test Learner",
        )

        profile_row = (
            False, "beginner", "English",
            "step_by_step", 45,
        )

        connection, cursor = self.make_database_mock(
            [user_row, (user_id,), profile_row]
        )

        with patch(
            "services.learner_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.learner_service.load_database_url",
            return_value="postgresql://test",
        ):
            learner = get_or_create_learner(self.claims)

        self.assertEqual(learner["user_id"], str(user_id))
        self.assertEqual(learner["role"], "student")
        self.assertTrue(learner["is_active"])
        self.assertFalse(learner["adult_confirmation"])
        self.assertTrue(learner["profile_created"])
        self.assertEqual(cursor.execute.call_count, 3)

    def test_existing_learner_profile_is_preserved(self):
        user_id = uuid4()

        user_row = (
            user_id, "student", True,
            "learner@gmail.com", True, "Test Learner",
        )

        profile_row = (
            False, "intermediate", "English",
            "example_first", 60,
        )

        connection, cursor = self.make_database_mock(
            [user_row, None, profile_row]
        )

        with patch(
            "services.learner_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.learner_service.load_database_url",
            return_value="postgresql://test",
        ):
            learner = get_or_create_learner(self.claims)

        self.assertFalse(learner["profile_created"])
        self.assertEqual(learner["proficiency_level"], "intermediate")
        self.assertEqual(learner["daily_study_minutes"], 60)

        self.assertEqual(cursor.execute.call_count, 3)

    def test_inactive_account_is_rejected(self):
        user_id = uuid4()

        connection, cursor = self.make_database_mock(
            [None, (user_id, False)]
        )

        with patch(
            "services.learner_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.learner_service.load_database_url",
            return_value="postgresql://test",
        ):
            with self.assertRaises(PermissionError):
                get_or_create_learner(self.claims)

        self.assertEqual(cursor.execute.call_count, 2)

    def test_missing_profile_is_rejected(self):
        user_id = uuid4()

        user_row = (
            user_id, "student", True,
            "learner@gmail.com", True, "Test Learner",
        )

        connection, cursor = self.make_database_mock(
            [user_row, (user_id,), None]
        )

        with patch(
            "services.learner_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.learner_service.load_database_url",
            return_value="postgresql://test",
        ):
            with self.assertRaises(RuntimeError):
                get_or_create_learner(self.claims)

    def test_invalid_adult_confirmation_user_id(self):
        with patch(
            "services.learner_service.psycopg.connect"
        ) as database:
            with self.assertRaises(ValueError):
                confirm_adult_status("invalid-id")

        database.assert_not_called()

    def test_adult_confirmation_updates_existing_profile(self):
        user_id = uuid4()
        connection, cursor = self.make_database_mock([])
        cursor.rowcount = 1

        with patch(
            "services.learner_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.learner_service.load_database_url",
            return_value="postgresql://test",
        ):
            result = confirm_adult_status(str(user_id))

        self.assertIsNone(result)
        self.assertEqual(cursor.execute.call_count, 1)
        self.assertEqual(
            cursor.execute.call_args[0][1],
            (user_id,),
        )

    def test_adult_confirmation_rejects_missing_profile(self):
        user_id = uuid4()
        connection, cursor = self.make_database_mock([])
        cursor.rowcount = 0

        with patch(
            "services.learner_service.psycopg.connect",
            return_value=connection,
        ), patch(
            "services.learner_service.load_database_url",
            return_value="postgresql://test",
        ):
            with self.assertRaises(ValueError):
                confirm_adult_status(str(user_id))


if __name__ == "__main__":
    unittest.main()
