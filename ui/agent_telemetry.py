"""Admin interface for aggregate AI Tutor run operations insights."""

import logging

import psycopg
import streamlit as st

from ui.theme import render_page_header

from services.agent_telemetry_insights_service import get_agent_run_summary


logger = logging.getLogger(__name__)

COURSE_SLUG = "python-basics"


def _format_duration(duration_ms: float | None) -> str:
    """Format a nullable millisecond duration for a metric or table."""

    if duration_ms is None:
        return "—"
    if duration_ms < 1000:
        return f"{duration_ms:.0f} ms"
    return f"{duration_ms / 1000:.2f} s"


def render_agent_telemetry(learner: dict) -> None:
    """Display privacy-preserving operational metrics for Tutor runs."""

    render_page_header(
        "ADMINISTRATOR WORKSPACE",
        "AI Tutor operations",
        "Monitor authenticated Tutor run reliability and execution time "
        "through privacy-preserving course-level metrics.",
    )

    if learner.get("role") != "admin":
        st.error("An active administrator account is required.")
        return

    try:
        summary = get_agent_run_summary(
            user_id=str(learner.get("user_id", "")),
            course_slug=COURSE_SLUG,
            days=14,
        )
    except PermissionError:
        st.error("An active administrator account is required.")
        return
    except (ValueError, LookupError):
        st.error("We could not load AI Tutor run insights.")
        return
    except (psycopg.Error, RuntimeError):
        logger.exception("Unable to load AI Tutor run insights.")
        st.error(
            "AI Tutor run insights are temporarily unavailable. "
            "Please try again."
        )
        return

    st.subheader("Run status — last 14 days")
    st.caption(
        "Runs still marked as running after 15 minutes are separated as "
        "stale/long-running. They may indicate an interrupted process; "
        "the underlying telemetry record is not changed."
    )

    status_columns = st.columns(6)
    status_columns[0].metric("Total runs", summary["total_runs"])
    status_columns[1].metric("Completed", summary["completed_runs"])
    status_columns[2].metric("Failed", summary["failed_runs"])
    status_columns[3].metric("Running", summary["running_runs"])
    status_columns[4].metric("Stale / long-running", summary["stale_runs"])
    status_columns[5].metric("Stopped", summary["stopped_runs"])

    st.subheader("Execution health")
    health_columns = st.columns(3)
    health_columns[0].metric(
        "Average completed duration",
        _format_duration(summary["average_completed_duration_ms"]),
        help="Average elapsed time for completed runs in the selected period.",
    )
    completed_share = summary["completed_share_percent"]
    health_columns[1].metric(
        "Completed share",
        f"{completed_share:.1f}%" if completed_share is not None else "—",
        help=(
            "Completed runs divided by finished runs. Running runs are "
            "excluded from this percentage."
        ),
    )
    failure_rate = summary["failure_rate_percent"]
    health_columns[2].metric(
        "Failure rate",
        f"{failure_rate:.1f}%" if failure_rate is not None else "—",
        help=(
            "Failed runs divided by finished runs. Running runs are "
            "excluded from this percentage."
        ),
    )

    st.divider()
    st.subheader("Daily run activity — last 14 days")

    if not summary["trend"]:
        st.info("There is no run activity to display yet.")
        return

    trend_rows = [
        {
            "Date": row["date"].strftime("%d %b %Y"),
            "Total": row["total_runs"],
            "Completed": row["completed_runs"],
            "Failed": row["failed_runs"],
            "Running": row["running_runs"],
            "Stale / long-running": row["stale_runs"],
            "Stopped": row["stopped_runs"],
            "Avg. completed duration": _format_duration(
                row["average_completed_duration_ms"]
            ),
        }
        for row in summary["trend"]
    ]

    if summary["total_runs"] == 0:
        st.info(
            "No authenticated persistent Tutor runs have been recorded "
            "for this course in the selected period."
        )

    st.dataframe(
        trend_rows,
        width="stretch",
        hide_index=True,
    )
