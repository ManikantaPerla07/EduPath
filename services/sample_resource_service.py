"""Repeatable import of the repository-authored Python starter resources."""

from hashlib import sha256
from pathlib import Path
from typing import Any

import psycopg

from services.document_service import (
    DocumentIngestionError,
    ingest_document,
    list_admin_course_topics,
    list_course_documents,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOCUMENTS_DIR = PROJECT_ROOT / "sample_documents"
SUPPORTED_COURSE_SLUG = "python-basics"
SAMPLE_SOURCE_LICENSE = "Original — EduPath project"
SAMPLE_RIGHTS_BASIS = "original"

SAMPLE_RESOURCE_MANIFEST = (
    {
        "file_name": "python_variables_intro_sanitized.md",
        "source_title": "Python Variables and Data Types",
        "topic_slug": "variables-data-types",
    },
    {
        "file_name": "python_operators_expressions.md",
        "source_title": "Python Operators and Expressions",
        "topic_slug": "operators",
    },
    {
        "file_name": "python_conditional_statements.md",
        "source_title": "Python Conditional Statements",
        "topic_slug": "conditionals",
    },
    {
        "file_name": "python_loops.md",
        "source_title": "Python Loops",
        "topic_slug": "loops",
    },
    {
        "file_name": "python_functions.md",
        "source_title": "Python Functions",
        "topic_slug": "functions",
    },
    {
        "file_name": "python_lists_and_tuples.md",
        "source_title": "Python Lists and Tuples",
        "topic_slug": "lists-tuples",
    },
    {
        "file_name": "python_dictionaries_and_sets.md",
        "source_title": "Python Dictionaries and Sets",
        "topic_slug": "dictionaries-sets",
    },
    {
        "file_name": "python_strings.md",
        "source_title": "Python Strings",
        "topic_slug": "strings",
    },
    {
        "file_name": "python_basic_problem_solving.md",
        "source_title": "Basic Problem Solving with Python",
        "topic_slug": "problem-solving",
    },
)


def import_sample_python_resources(
    user_id: str,
    course_slug: str = SUPPORTED_COURSE_SLUG,
) -> dict[str, Any]:
    """Import missing original sample notes without duplicating existing files.

    The importer is administrator-gated through the existing document
    services. Existing file hashes are compared before insertion, so the
    operation can safely be repeated. It deliberately does not generate
    Gemini embeddings; embedding generation remains an explicit admin action.
    """

    if course_slug != SUPPORTED_COURSE_SLUG:
        raise ValueError(
            "The sample resource pack is only mapped to python-basics."
        )

    topics = list_admin_course_topics(user_id, course_slug)
    topic_slugs = {topic["topic_slug"] for topic in topics}
    missing_topics = sorted({
        item["topic_slug"]
        for item in SAMPLE_RESOURCE_MANIFEST
        if item["topic_slug"] not in topic_slugs
    })
    if missing_topics:
        raise ValueError(
            "The Python course is missing expected topics: "
            + ", ".join(missing_topics)
        )

    existing_documents = list_course_documents(user_id, course_slug)
    existing_by_hash = {
        document["file_sha256"]: document
        for document in existing_documents
        if document.get("file_sha256")
    }

    # Read all files first. A missing repository asset must not result in a
    # partially imported pack.
    resources_to_import = []
    for item in SAMPLE_RESOURCE_MANIFEST:
        file_path = SAMPLE_DOCUMENTS_DIR / item["file_name"]
        try:
            file_data = file_path.read_bytes()
        except OSError as exc:
            raise RuntimeError(
                f"Sample resource is unavailable: {item['file_name']}."
            ) from exc

        if not file_data:
            raise ValueError(
                f"Sample resource is empty: {item['file_name']}."
            )

        resources_to_import.append((item, file_data, sha256(file_data).hexdigest()))

    results = []
    for item, file_data, file_hash in resources_to_import:
        existing = existing_by_hash.get(file_hash)

        if existing is not None:
            existing_topic = existing.get("topic_slug")
            if existing_topic != item["topic_slug"]:
                results.append({
                    **item,
                    "status": "topic_mismatch",
                    "document_id": existing["document_id"],
                    "message": (
                        "This exact file already exists but is associated "
                        "with a different topic. Review it in the inventory."
                    ),
                })
            elif existing.get("archived_at") is not None:
                results.append({
                    **item,
                    "status": "archived",
                    "document_id": existing["document_id"],
                    "message": (
                        "This resource already exists but is archived. "
                        "Restore it from the inventory after review."
                    ),
                })
            else:
                results.append({
                    **item,
                    "status": "already_present",
                    "document_id": existing["document_id"],
                    "message": (
                        "This exact resource is already stored for its topic."
                    ),
                })
            continue

        try:
            imported = ingest_document(
                user_id=user_id,
                course_slug=course_slug,
                file_name=item["file_name"],
                file_data=file_data,
                source_title=item["source_title"],
                source_license=SAMPLE_SOURCE_LICENSE,
                rights_basis=SAMPLE_RIGHTS_BASIS,
                topic_slug=item["topic_slug"],
            )
        except PermissionError:
            # Stop immediately if the admin account becomes inactive or loses
            # its role during the multi-resource import.
            raise
        except (OSError, ValueError, DocumentIngestionError, psycopg.Error) as exc:
            results.append({
                **item,
                "status": "failed",
                "message": f"Import failed: {type(exc).__name__}.",
            })
            continue

        imported["status"] = "imported"
        results.append(imported)
        existing_by_hash[file_hash] = {
            "document_id": imported["document_id"],
            "topic_slug": item["topic_slug"],
            "archived_at": None,
        }

    counts = {
        status: sum(result["status"] == status for result in results)
        for status in (
            "imported",
            "already_present",
            "archived",
            "topic_mismatch",
            "failed",
        )
    }

    return {
        "course_slug": course_slug,
        "total_resources": len(SAMPLE_RESOURCE_MANIFEST),
        **counts,
        "resources": results,
    }
