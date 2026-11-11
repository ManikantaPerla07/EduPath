"""Administrator interface for the EduPath educational knowledge base."""

import logging

import streamlit as st

from services.document_service import (
    DocumentIngestionError,
    ingest_document,
    list_admin_course_topics,
    list_admin_courses,
    list_course_documents,
    retry_document_processing,
)
from services.embedding_service import embed_pending_document_chunks


logger = logging.getLogger(__name__)

RIGHTS_BASIS_OPTIONS = {
    "Original work": "original",
    "Public domain": "public_domain",
    "Open license": "open_license",
    "Permission obtained": "permission_obtained",
    "Uploader has the necessary rights": "user_has_rights",
}


def _embedding_status(document: dict) -> str:
    """Describe whether all persisted chunks have vector embeddings."""

    total = int(document.get("chunk_count") or 0)
    embedded = int(document.get("embedded_chunk_count") or 0)

    if total < 1:
        return "No chunks"
    if embedded >= total:
        return "Complete"
    if embedded == 0:
        return f"Pending ({total} chunks)"
    return f"Partial ({embedded}/{total})"


def _format_file_size(size_bytes: int) -> str:
    """Format a document size for display."""

    return f"{size_bytes / (1024 * 1024):.2f} MB"


def _show_admin_notice() -> None:
    notice = st.session_state.pop("edupath_knowledge_notice", None)

    if notice:
        st.success(notice)


def _render_document_inventory(
    user_id: str,
    course_slug: str,
) -> None:
    """Display document processing and embedding status for a course."""

    st.subheader("Knowledge resource inventory")

    try:
        documents = list_course_documents(
            user_id=user_id,
            course_slug=course_slug,
        )
    except PermissionError:
        st.error("An active administrator account is required.")
        return
    except Exception:
        logger.exception("Unable to load the EduPath knowledge inventory.")
        st.error("We could not load the knowledge resources. Please retry.")
        return

    if not documents:
        st.info("No learning resources have been uploaded for this course yet.")
        return

    for document in documents:
        document_id = document["document_id"]
        status = document["processing_status"]

        with st.container(border=True):
            heading_columns = st.columns([3, 1])
            heading_columns[0].markdown(
                f"**{document['source_title']}**"
            )
            heading_columns[1].caption(status.replace("_", " ").title())

            st.caption(
                f"{document['file_name']} · "
                f"{_format_file_size(document['file_size_bytes'])}"
            )

            metadata_columns = st.columns(3)
            metadata_columns[0].metric(
                "Text chunks",
                document["chunk_count"],
            )
            metadata_columns[1].metric(
                "Embeddings",
                f"{document['embedded_chunk_count']}/"
                f"{document['chunk_count']}",
            )
            metadata_columns[2].metric(
                "Embedding status",
                _embedding_status(document),
            )

            topic_name = document.get("topic_name") or "Entire course"
            st.caption(
                f"Topic: {topic_name} · "
                f"Rights basis: {document['rights_basis']} · "
                f"License: {document['source_license']}"
            )

            error_message = document.get("error_message")
            if error_message:
                st.warning(f"Processing note: {error_message}")

            action_columns = st.columns(2)

            if status == "failed":
                if action_columns[0].button(
                    "Retry extraction and chunking",
                    key=f"edupath_retry_document_{document_id}",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Reprocessing the stored document..."):
                            result = retry_document_processing(
                                user_id=user_id,
                                document_id=document_id,
                            )
                        st.session_state["edupath_knowledge_notice"] = (
                            f"Document reprocessed successfully: "
                            f"{result['chunk_count']} chunks are ready. "
                            "Generate their embeddings next."
                        )
                        st.rerun()
                    except (ValueError, LookupError, PermissionError) as exc:
                        st.error(str(exc))
                    except DocumentIngestionError:
                        logger.exception(
                            "Administrator document retry failed."
                        )
                        st.error(
                            "The document could not be reprocessed. "
                            "Its failed status has been preserved."
                        )
                    except Exception:
                        logger.exception(
                            "Unexpected error while retrying a document."
                        )
                        st.error("The document retry failed. Please try again.")

            elif (
                status == "ready"
                and document["chunk_count"] > document["embedded_chunk_count"]
            ):
                if action_columns[0].button(
                    "Generate missing embeddings",
                    key=f"edupath_embed_document_{document_id}",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner(
                            "Generating embeddings for remaining chunks..."
                        ):
                            result = embed_pending_document_chunks(
                                document_id=document_id,
                            )
                        st.session_state["edupath_knowledge_notice"] = (
                            f"Embedding run finished: "
                            f"{result['embeddings_saved']} new vectors saved; "
                            f"{result['skipped_due_to_concurrent_update']} "
                            "chunks were already processed elsewhere."
                        )
                        st.rerun()
                    except Exception:
                        logger.exception(
                            "Administrator document embedding failed."
                        )
                        st.error(
                            "Embedding generation did not finish. "
                            "Any vectors already saved were preserved; "
                            "you can retry the missing embeddings."
                        )

            if document["processing_status"] == "ready":
                st.caption(
                    "The text is available to retrieval. Documents with "
                    "pending embeddings are not yet fully searchable."
                )


def render_knowledge_management(learner: dict) -> None:
    """Render the administrator-only educational resource workspace."""

    st.title("Knowledge Management")
    st.write(
        "Upload approved learning resources, inspect their processing "
        "status, and manage missing vector embeddings."
    )

    if learner.get("role") != "admin":
        st.error(
            "This workspace is available only to active EduPath administrators."
        )
        return

    user_id = str(learner.get("user_id") or "")
    if not user_id:
        st.error("The authenticated administrator identity is unavailable.")
        return

    _show_admin_notice()

    try:
        courses = list_admin_courses(user_id)
    except PermissionError:
        st.error("An active administrator account is required.")
        return
    except Exception:
        logger.exception("Unable to load courses for knowledge management.")
        st.error("We could not load the course catalog. Please retry.")
        return

    if not courses:
        st.info("No courses are configured yet.")
        return

    course_labels = {
        f"{course['course_name']} ({course['course_slug']})": course
        for course in courses
    }
    selected_label = st.selectbox(
        "Course",
        options=list(course_labels),
        key="edupath_knowledge_course",
    )
    selected_course = course_labels[selected_label]
    course_slug = selected_course["course_slug"]

    if not selected_course["is_published"]:
        st.warning(
            "This course is currently unpublished. Resources can be prepared "
            "now, but learner access depends on the course publication policy."
        )

    try:
        topics = list_admin_course_topics(
            user_id=user_id,
            course_slug=course_slug,
        )
    except Exception:
        logger.exception("Unable to load topics for the selected course.")
        st.error("We could not load this course's topics.")
        return

    topic_labels = {"Entire course (not topic-specific)": None}
    for topic in topics:
        topic_labels[
            f"{topic['sequence_number']}. {topic['topic_name']}"
        ] = topic["topic_slug"]

    st.divider()
    st.subheader("Upload a learning resource")
    st.caption(
        "PDF, TXT and Markdown files up to 5 MB are supported. "
        "Provide accurate source and rights information before uploading."
    )

    with st.form("edupath_knowledge_upload_form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "Resource file",
            type=["pdf", "txt", "md"],
        )
        source_title = st.text_input(
            "Source title",
            placeholder="e.g. Python Variables and Data Types",
        )
        source_license = st.text_input(
            "Source license",
            placeholder="e.g. Original, CC BY 4.0, Public Domain",
        )
        selected_topic_label = st.selectbox(
            "Topic association",
            options=list(topic_labels),
        )
        selected_rights_label = st.selectbox(
            "Rights basis",
            options=list(RIGHTS_BASIS_OPTIONS),
        )
        submitted = st.form_submit_button(
            "Upload and extract text",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if uploaded_file is None:
            st.error("Choose a PDF, TXT or Markdown file first.")
        else:
            try:
                with st.spinner("Validating and extracting document text..."):
                    result = ingest_document(
                        user_id=user_id,
                        course_slug=course_slug,
                        file_name=uploaded_file.name,
                        file_data=uploaded_file.getvalue(),
                        source_title=source_title,
                        source_license=source_license,
                        rights_basis=RIGHTS_BASIS_OPTIONS[
                            selected_rights_label
                        ],
                        topic_slug=topic_labels[selected_topic_label],
                    )
                st.session_state["edupath_knowledge_notice"] = (
                    f"Uploaded {result['file_name']} and created "
                    f"{result['chunk_count']} text chunks. "
                    "Generate embeddings from the inventory below."
                )
                st.rerun()
            except (ValueError, LookupError, PermissionError) as exc:
                st.error(str(exc))
            except DocumentIngestionError:
                logger.exception("Administrator document ingestion failed.")
                st.error(
                    "The resource could not be fully processed. "
                    "Check the inventory for its processing status."
                )
            except Exception:
                logger.exception("Unexpected administrator upload error.")
                st.error("The resource could not be uploaded. Please try again.")

    st.divider()
    _render_document_inventory(
        user_id=user_id,
        course_slug=course_slug,
    )
