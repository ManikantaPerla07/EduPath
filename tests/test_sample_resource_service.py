"""Tests for the repeatable Python sample-resource import workflow."""

from hashlib import sha256
import tempfile
import unittest
from unittest.mock import patch

from services.sample_resource_service import (
    SAMPLE_RESOURCE_MANIFEST,
    import_sample_python_resources,
)


USER_ID = "11111111-1111-4111-8111-111111111111"


class SampleResourceImportTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_dir = Path(self.temp_dir.name)
        self.file_data = {}

        for index, item in enumerate(SAMPLE_RESOURCE_MANIFEST, start=1):
            data = (
                f"# {item['source_title']}\n\n"
                f"Original EduPath sample note {index}.\n"
            ).encode("utf-8")
            (self.sample_dir / item["file_name"]).write_bytes(data)
            self.file_data[item["file_name"]] = data

        self.topics = [
            {"topic_slug": item["topic_slug"]}
            for item in SAMPLE_RESOURCE_MANIFEST
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def _existing_document(self, item, status="ready", archived_at=None):
        data = self.file_data[item["file_name"]]
        return {
            "document_id": f"document-{item['topic_slug']}",
            "file_name": item["file_name"],
            "file_sha256": sha256(data).hexdigest(),
            "topic_slug": item["topic_slug"],
            "processing_status": status,
            "archived_at": archived_at,
        }

    @patch("services.sample_resource_service.ingest_document")
    @patch("services.sample_resource_service.list_course_documents")
    @patch("services.sample_resource_service.list_admin_course_topics")
    def test_imports_missing_resources_and_skips_exact_existing_hashes(
        self,
        list_topics,
        list_documents,
        ingest,
    ):
        existing_item = SAMPLE_RESOURCE_MANIFEST[0]
        list_topics.return_value = self.topics
        list_documents.return_value = [
            self._existing_document(existing_item)
        ]
        ingest.side_effect = lambda **kwargs: {
            "document_id": f"new-{kwargs['topic_slug']}",
            "file_name": kwargs["file_name"],
            "topic_slug": kwargs["topic_slug"],
            "chunk_count": 2,
            "processing_status": "ready",
        }

        with patch(
            "services.sample_resource_service.SAMPLE_DOCUMENTS_DIR",
            self.sample_dir,
        ):
            result = import_sample_python_resources(USER_ID)

        self.assertEqual(result["total_resources"], 9)
        self.assertEqual(result["imported"], 8)
        self.assertEqual(result["already_present"], 1)
        self.assertEqual(result["archived"], 0)
        self.assertEqual(result["topic_mismatch"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(len(result["resources"]), 9)
        self.assertEqual(ingest.call_count, 8)

        first_call = ingest.call_args_list[0].kwargs
        self.assertEqual(first_call["user_id"], USER_ID)
        self.assertEqual(first_call["course_slug"], "python-basics")
        self.assertEqual(first_call["source_license"], "Original — EduPath project")
        self.assertEqual(first_call["rights_basis"], "original")
        self.assertEqual(first_call["topic_slug"], "operators")

    @patch("services.sample_resource_service.ingest_document")
    @patch("services.sample_resource_service.list_course_documents")
    @patch("services.sample_resource_service.list_admin_course_topics")
    def test_repeat_import_skips_all_exact_resource_hashes(
        self,
        list_topics,
        list_documents,
        ingest,
    ):
        list_topics.return_value = self.topics
        list_documents.return_value = [
            self._existing_document(item)
            for item in SAMPLE_RESOURCE_MANIFEST
        ]

        with patch(
            "services.sample_resource_service.SAMPLE_DOCUMENTS_DIR",
            self.sample_dir,
        ):
            result = import_sample_python_resources(USER_ID)

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["already_present"], 9)
        ingest.assert_not_called()

    @patch("services.sample_resource_service.ingest_document")
    @patch("services.sample_resource_service.list_course_documents")
    @patch("services.sample_resource_service.list_admin_course_topics")
    def test_archived_exact_resource_is_reported_not_duplicated(
        self,
        list_topics,
        list_documents,
        ingest,
    ):
        item = SAMPLE_RESOURCE_MANIFEST[0]
        list_topics.return_value = self.topics
        list_documents.return_value = [
            self._existing_document(item, archived_at="archived")
        ]

        with patch(
            "services.sample_resource_service.SAMPLE_DOCUMENTS_DIR",
            self.sample_dir,
        ):
            result = import_sample_python_resources(USER_ID)

        self.assertEqual(result["archived"], 1)
        self.assertEqual(result["imported"], 8)
        self.assertEqual(result["resources"][0]["status"], "archived")
        self.assertEqual(
            result["resources"][0]["document_id"],
            f"document-{item['topic_slug']}",
        )
        self.assertEqual(ingest.call_count, 8)

    @patch("services.sample_resource_service.ingest_document")
    @patch("services.sample_resource_service.list_course_documents")
    @patch("services.sample_resource_service.list_admin_course_topics")
    def test_existing_hash_with_wrong_topic_is_reported_without_duplicate(
        self,
        list_topics,
        list_documents,
        ingest,
    ):
        item = SAMPLE_RESOURCE_MANIFEST[0]
        list_topics.return_value = self.topics
        existing = self._existing_document(item)
        existing["topic_slug"] = "operators"
        list_documents.return_value = [existing]

        with patch(
            "services.sample_resource_service.SAMPLE_DOCUMENTS_DIR",
            self.sample_dir,
        ):
            result = import_sample_python_resources(USER_ID)

        self.assertEqual(result["topic_mismatch"], 1)
        self.assertEqual(result["imported"], 8)
        self.assertEqual(
            result["resources"][0]["status"],
            "topic_mismatch",
        )
        ingest.assert_not_called() if result["imported"] == 0 else None
        self.assertEqual(ingest.call_count, 8)

    @patch("services.sample_resource_service.list_admin_course_topics")
    def test_rejects_wrong_course_before_database_inventory_lookup(
        self,
        list_topics,
    ):
        with self.assertRaisesRegex(ValueError, "only mapped to python-basics"):
            import_sample_python_resources(USER_ID, "another-course")

        list_topics.assert_not_called()

    @patch("services.sample_resource_service.list_course_documents")
    @patch("services.sample_resource_service.list_admin_course_topics")
    def test_rejects_when_expected_course_topic_is_missing(
        self,
        list_topics,
        list_documents,
    ):
        list_topics.return_value = self.topics[:-1]

        with self.assertRaisesRegex(ValueError, "problem-solving"):
            import_sample_python_resources(USER_ID)

        list_documents.assert_not_called()


if __name__ == "__main__":
    unittest.main()
