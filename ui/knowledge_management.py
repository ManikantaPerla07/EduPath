"""Administrator interface for the EduPath educational knowledge base."""

import logging

import streamlit as st

from ui.theme import render_page_header

from services.document_service import (
    DocumentIngestionError,
    archive_course_document,
    ingest_document,
    list_admin_course_topics,
    list_admin_courses,
    list_course_documents,
    restore_course_document,
    retry_document_processing,
)
from services.course_service import (
    get_admin_course_publication_status,
    set_course_publication_status,
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
            display_status = (
                "Archived"
                if document.get("archived_at") is not None
                else status.replace("_", " ").title()
            )
            heading_columns[1].caption(display_status)

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

            if document.get("archived_at") is not None:
                if action_columns[0].button(
                    "Restore resource",
                    key=f"edupath_restore_document_{document_id}",
                    width="stretch",
                ):
                    try:
                        result = restore_course_document(
                            user_id=user_id,
                            document_id=document_id,
                        )
                        st.session_state["edupath_knowledge_notice"] = (
                            "The resource has been restored. "
                            "Its existing chunks and embeddings were preserved. "
                            "Publish the course again only after reviewing readiness."
                        )
                        st.rerun()
                    except (ValueError, LookupError, PermissionError) as exc:
                        st.error(str(exc))
                    except Exception:
                        logger.exception("Unable to restore archived resource.")
                        st.error("The resource could not be restored.")

            else:
                archive_confirmation_key = (
                    f"edupath_confirm_archive_{document_id}"
                )

                if status == "processing":
                    action_columns[1].caption(
                        "Archiving is disabled while processing."
                    )
                elif action_columns[1].button(
                    "Archive resource",
                    key=f"edupath_archive_document_{document_id}",
                    width="stretch",
                ):
                    st.session_state[archive_confirmation_key] = True

                if st.session_state.get(archive_confirmation_key):
                    with st.form(
                        f"edupath_archive_confirmation_{document_id}"
                    ):
                        confirmed = st.checkbox(
                            "I understand this resource will stop being used "
                            "for AI Tutor retrieval. Its stored file and "
                            "embeddings will be preserved."
                        )
                        confirm_archive = st.form_submit_button(
                            "Confirm archive",
                            type="primary",
                        )

                    if confirm_archive:
                        if not confirmed:
                            st.error("Confirm the archival action first.")
                        else:
                            try:
                                result = archive_course_document(
                                    user_id=user_id,
                                    document_id=document_id,
                                )
                                st.session_state.pop(
                                    archive_confirmation_key,
                                    None,
                                )
                                message = (
                                    "Resource archived. Its original file, "
                                    "chunks and embeddings remain stored."
                                )
                                if result["course_unpublished"]:
                                    message += (
                                        " The course was also unpublished "
                                        "because this was its last fully "
                                        "embedded active resource."
                                    )
                                st.session_state[
                                    "edupath_knowledge_notice"
                                ] = message
                                st.rerun()
                            except (ValueError, LookupError, PermissionError) as exc:
                                st.error(str(exc))
                            except Exception:
                                logger.exception(
                                    "Unable to archive educational resource."
                                )
                                st.error("The resource could not be archived.")

            if (
                document.get("archived_at") is None
                and status == "failed"
            ):
                if action_columns[0].button(
                    "Retry extraction and chunking",
                    key=f"edupath_retry_document_{document_id}",
                    width="stretch",
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
                document.get("archived_at") is None
                and status == "ready"
                and document["chunk_count"] > document["embedded_chunk_count"]
            ):
                if action_columns[0].button(
                    "Generate missing embeddings",
                    key=f"edupath_embed_document_{document_id}",
                    width="stretch",
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

            if (
                document.get("archived_at") is None
                and document["processing_status"] == "ready"
            ):
                st.caption(
                    "Text extraction is complete. Semantic retrieval can use "
                    "only chunks whose embeddings have been stored."
                )


def render_knowledge_management(learner: dict) -> None:
    """Render the administrator-only educational resource workspace."""

    render_page_header(
        "ADMINISTRATOR WORKSPACE",
        "Knowledge management",
        "Manage approved learning resources, monitor processing status, "
        "and keep course embeddings ready for retrieval.",
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

    try:
        publication = get_admin_course_publication_status(
            user_id=user_id,
            course_slug=course_slug,
        )
    except Exception:
        logger.exception("Unable to load course publication readiness.")
        st.error("We could not load course publication status.")
        return

    st.subheader("Course publication")
    st.caption(
        "Learners can access this course only while it is published. "
        "Publishing requires every topic to have an active, topic-specific "
        "resource with all embeddings stored, as well as active assessment "
        "questions."
    )
    readiness_columns = st.columns(4)
    readiness_columns[0].metric("Topics", publication["topic_count"])
    readiness_columns[1].metric(
        "Topics covered",
        f"{publication['covered_topic_count']}/{publication['topic_count']}",
    )
    readiness_columns[2].metric(
        "Active questions",
        publication["active_question_count"],
    )
    readiness_columns[3].metric(
        "Fully embedded resources",
        publication["fully_embedded_document_count"],
    )

    topic_count = publication["topic_count"]
    covered_topic_count = publication["covered_topic_count"]
    coverage_ratio = (
        covered_topic_count / topic_count
        if topic_count > 0
        else 0.0
    )
    st.progress(
        coverage_ratio,
        text=(
            f"Topic resource coverage: {covered_topic_count} of "
            f"{topic_count} topics"
        ),
    )

    st.subheader("Topic resource coverage")
    st.caption(
        "A topic is covered only when it has at least one non-archived, "
        "ready resource assigned to that topic and every extracted chunk "
        "has an embedding. Course-wide resources are listed in the inventory "
        "but do not replace topic-specific coverage."
    )

    coverage_rows = []
    for topic in publication["topic_coverage"]:
        if topic["is_covered"]:
            coverage_status = "Covered"
        elif topic["chunk_count"] > topic["embedded_chunk_count"]:
            coverage_status = "Embedding incomplete"
        else:
            coverage_status = "Resource needed"

        coverage_rows.append({
            "Topic": topic["topic_name"],
            "Fully embedded resources": topic["fully_embedded_document_count"],
            "Embedded chunks": (
                f"{topic['embedded_chunk_count']}/"
                f"{topic['chunk_count']}"
                if topic["chunk_count"]
                else "—"
            ),
            "Coverage": coverage_status,
        })

    st.dataframe(
        coverage_rows,
        width="stretch",
        height="content",
        hide_index=True,
    )
    st.caption(
        "A topic is covered when at least one active, topic-specific resource "
        "has all its chunks embedded. The chunk total includes other active "
        "resources too, so it can be incomplete even when coverage is met."
    )

    if publication["uncovered_topics"]:
        st.warning(
            "Resources are still needed for: "
            + ", ".join(
                topic["topic_name"]
                for topic in publication["topic_coverage"]
                if not topic["is_covered"]
            )
        )

    st.caption(
        "Publication readiness: "
        + ("Ready" if publication["ready_to_publish"] else "Not ready")
    )

    with st.form("edupath_course_publication_form"):
        confirm_publication_change = st.checkbox(
            (
                "I confirm that learners should be able to access this course."
                if not publication["is_published"]
                else "I confirm that learner access to this course should be paused."
            )
        )
        publication_submitted = st.form_submit_button(
            "Publish course"
            if not publication["is_published"]
            else "Unpublish course",
            type="primary",
            width="stretch",
            disabled=(
                not publication["ready_to_publish"]
                and not publication["is_published"]
            ),
        )

    if publication_submitted:
        if not confirm_publication_change:
            st.error("Confirm the course publication change first.")
        else:
            try:
                result = set_course_publication_status(
                    user_id=user_id,
                    course_slug=course_slug,
                    is_published=not publication["is_published"],
                )
                st.session_state["edupath_knowledge_notice"] = (
                    "Course published successfully."
                    if result["is_published"]
                    else "Course unpublished. Learner access is paused."
                )
                st.rerun()
            except (ValueError, LookupError, PermissionError) as exc:
                st.error(str(exc))
            except Exception:
                logger.exception("Unable to change course publication status.")
                st.error("The course publication status could not be changed.")

    if not publication["is_published"]:
        st.warning(
            "This course is currently unpublished. Learners cannot access "
            "its assessment, progress, study-plan or tutor resources."
        )

    st.divider()

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
        st.caption(
            "Choose a specific topic for this file to count toward that "
            "topic's coverage. 'Entire course' resources are supplemental "
            "and do not replace topic-specific resources."
        )
        selected_rights_label = st.selectbox(
            "Rights basis",
            options=list(RIGHTS_BASIS_OPTIONS),
        )
        submitted = st.form_submit_button(
            "Upload and extract text",
            type="primary",
            width="stretch",
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
