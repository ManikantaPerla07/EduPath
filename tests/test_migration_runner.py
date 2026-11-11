"""Tests for EduPath's application migration verifier."""

import unittest
from unittest.mock import MagicMock

from database.run_migrations import (
    EXPECTED_INDEXES,
    EXPECTED_TABLES,
    verify_database,
)


class MigrationVerificationTests(unittest.TestCase):

    def make_connection(self, existing_indexes=None):
        connection = MagicMock()
        cursor = MagicMock()

        connection.cursor.return_value.__enter__.return_value = cursor
        connection.cursor.return_value.__exit__.return_value = False

        cursor.fetchall.side_effect = [
            [(name,) for name in sorted(EXPECTED_TABLES)],
            [
                (name,)
                for name in sorted(
                    EXPECTED_INDEXES
                    if existing_indexes is None
                    else existing_indexes
                )
            ],
        ]
        cursor.fetchone.side_effect = [(True,), (True,)]

        return connection, cursor

    def test_verifies_expected_tables_constraints_and_indexes(self):
        connection, cursor = self.make_connection()

        table_count = verify_database(connection)

        self.assertEqual(table_count, len(EXPECTED_TABLES))
        self.assertEqual(cursor.execute.call_count, 4)
        index_query = cursor.execute.call_args_list[3].args[0]
        self.assertIn("FROM pg_indexes", index_query)
        self.assertIn("schemaname = 'public'", index_query)
        self.assertEqual(
            cursor.execute.call_args_list[3].args[1],
            (sorted(EXPECTED_INDEXES),),
        )

    def test_rejects_missing_performance_index(self):
        existing = EXPECTED_INDEXES - {"idx_agent_runs_active_session"}
        connection, cursor = self.make_connection(existing_indexes=existing)

        with self.assertRaisesRegex(
            RuntimeError,
            "Missing performance indexes",
        ):
            verify_database(connection)

        self.assertEqual(cursor.execute.call_count, 4)


if __name__ == "__main__":
    unittest.main()
