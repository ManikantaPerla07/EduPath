"""Admin interface for aggregate AI Tutor answer-feedback insights."""

import logging

import psycopg
import streamlit as st

from ui.theme import render_page_header

from services.tutor_feedback_service import get_tutor_feedback_summary


logger = logging.getLogger(__name__)

COURSE_SLUG = "python-basics"


def render_tutor_feedback(learner: dict) -> None:
    """Display course-level feedback metrics without exposing learner data."""

    render_page_header(
        "ADMINISTRATOR WORKSPACE",
        "AI Tutor feedback",
        "Review aggregate learner ratings, feedback coverage, and daily trends. "
        "Only course-level metrics are shown; learner identities and private "
        "conversation text are not exposed.",
    )

    if learner.get("role") != "admin":
        st.error("An active administrator account is required.")
        return

    try:
        summary = get_tutor_feedback_summary(
            user_id=str(learner.get("user_id", "")),
            course_slug=COURSE_SLUG,
            days=14,
        )
    except PermissionError:
        st.error("An active administrator account is required.")
        return
    except (ValueError, LookupError):
        st.error("We could not load AI Tutor feedback insights.")
        return
    except (psycopg.Error, RuntimeError):
        logger.exception("Unable to load AI Tutor feedback insights.")
        st.error(
            "Feedback insights are temporarily unavailable. Please try again."
        )
        return

    st.subheader("Overall feedback")

    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Assistant answers",
        summary["assistant_answer_count"],
    )
    metric_columns[1].metric(
        "Rated answers",
        summary["rated_answer_count"],
    )
    metric_columns[2].metric(
        "Helpful",
        summary["helpful_count"],
    )
    metric_columns[3].metric(
        "Not helpful",
        summary["not_helpful_count"],
    )

    coverage = summary["rating_coverage_percent"]
    helpful_rate = summary["helpful_percent"]

    rate_columns = st.columns(2)
    rate_columns[0].metric(
        "Feedback coverage",
        f"{coverage:.1f}%" if coverage is not None else "—",
        help=(
            "Percentage of saved AI Tutor answers that received "
            "a thumbs-up or thumbs-down rating."
        ),
    )
    rate_columns[1].metric(
        "Helpful rating share",
        f"{helpful_rate:.1f}%" if helpful_rate is not None else "—",
        help=(
            "Percentage of submitted ratings that were thumbs-up. "
            "Unrated answers are not included."
        ),
    )

    st.divider()
    st.subheader("Daily feedback — last 14 days")

    if not summary["trend"]:
        st.info("There is no feedback activity to display yet.")
        return

    trend_rows = [
        {
            "Date": row["date"].strftime("%d %b %Y"),
            "Ratings": row["rated_count"],
            "Helpful": row["helpful_count"],
            "Not helpful": row["not_helpful_count"],
        }
        for row in summary["trend"]
    ]

    if summary["rated_answer_count"] == 0:
        st.info(
            "No answer ratings have been submitted yet. "
            "The daily table will populate as learners rate Tutor answers."
        )

    st.dataframe(
        trend_rows,
        width="stretch",
        hide_index=True,
    )
