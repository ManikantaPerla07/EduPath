
"""Streamlit interface for personalized study plans."""

from collections import defaultdict
from datetime import date, datetime

import psycopg
import streamlit as st

from ui.theme import render_page_header
from services.course_service import is_course_published

from services.study_plan_service import (
    fetch_active_study_plan,
    generate_study_plan,
    update_study_plan_item_status,
)


_ACTIVITY_LABELS = {
    "learn": "Learn core concepts",
    "revision": "Revise this topic",
    "practice": "Focused practice",
    "spaced_review": "Spaced review",
}

_STATUS_LABELS = {
    "pending": "Pending",
    "in_progress": "In progress",
    "completed": "Completed",
    "skipped": "Skipped",
}


def _format_date(value):
    """Format database date values consistently for display."""

    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        return value.strftime("%A, %d %b %Y")

    return str(value)


def _handle_activity_update(user_id, item, new_status):
    """Save an activity status change and refresh the page."""

    plan_item_id = item.get("plan_item_id")

    if not plan_item_id:
        st.error("This activity is missing its database ID.")
        return

    try:
        result = update_study_plan_item_status(
            user_id=str(user_id),
            plan_item_id=str(plan_item_id),
            status=new_status,
        )

        completed = result["completed_activities"]
        total = result["total_activities"]
        percent = result["completion_percent"]

        if new_status == "completed":
            action = "marked as completed"
        else:
            action = "reopened"

        plan_message = (
            " Your entire study plan is now completed!"
            if result["plan_status"] == "completed"
            else ""
        )

        st.session_state["study_plan_notice"] = (
            f"Activity {action}. "
            f"Progress: {completed}/{total} activities ({percent:.2f}%)."
            f"{plan_message}"
        )

        st.rerun()

    except PermissionError as error:
        st.error(str(error))
    except ValueError as error:
        st.error(f"Invalid activity update: {error}")
    except (RuntimeError, psycopg.Error):
        st.error(
            "We couldn't update this activity right now. "
            "Please try again."
        )


def _display_plan(plan, user_id):
    """Render a saved plan and its scheduled activities."""

    items = plan.get("items", [])

    if not items:
        st.info("This study plan does not contain any activities yet.")
        return

    start_date = plan.get("start_date")
    end_date = plan.get("end_date")
    duration_days = plan.get("duration_days")

    if duration_days is None and start_date and end_date:
        start = (
            start_date.date()
            if isinstance(start_date, datetime)
            else start_date
        )
        end = (
            end_date.date()
            if isinstance(end_date, datetime)
            else end_date
        )

        if isinstance(start, date) and isinstance(end, date):
            duration_days = (end - start).days + 1

    completed_count = sum(
        item.get("status") == "completed"
        for item in items
    )
    total_count = len(items)
    remaining_count = total_count - completed_count
    total_minutes = sum(
        int(item.get("estimated_minutes") or 0)
        for item in items
    )

    completion_ratio = completed_count / total_count
    plan_status = plan.get("status", "active")

    st.subheader(plan.get("title") or "Your Python study plan")

    st.caption(
        f"{_format_date(start_date)} – {_format_date(end_date)}"
        if start_date and end_date
        else "Your saved personalized learning schedule"
    )

    if plan_status == "completed":
        st.success("Congratulations! You have completed your study plan.")
    else:
        st.caption("Plan status: In progress")

    metrics = st.columns(4)

    metrics[0].metric(
        "Plan duration",
        f"{duration_days or '—'} days",
    )
    metrics[1].metric("Total activities", total_count)
    metrics[2].metric("Completed", completed_count)
    metrics[3].metric("Remaining", remaining_count)

    st.progress(
        completion_ratio,
        text=f"Plan completion: {completion_ratio:.0%}",
    )

    st.caption(
        f"Estimated total study time: {total_minutes} minutes"
    )

    activities_by_date = defaultdict(list)

    for item in items:
        activities_by_date[str(item.get("scheduled_date"))].append(item)

    st.divider()
    st.subheader("Your schedule")

    for day_index, (scheduled_date, day_items) in enumerate(
        activities_by_date.items()
    ):
        day_minutes = sum(
            int(item.get("estimated_minutes") or 0)
            for item in day_items
        )

        with st.expander(
            f"{_format_date(day_items[0].get('scheduled_date'))} · "
            f"{day_minutes} minutes · {len(day_items)} activity(ies)",
            expanded=day_index == 0,
        ):
            for item_index, item in enumerate(day_items):
                topic_name = item.get("topic_name") or "Python topic"

                activity = _ACTIVITY_LABELS.get(
                    item.get("activity_type"),
                    str(
                        item.get("activity_type") or "Study activity"
                    ).replace("_", " ").title(),
                )

                current_status = item.get("status") or "pending"

                status_label = _STATUS_LABELS.get(
                    current_status,
                    current_status.replace("_", " ").title(),
                )

                st.markdown(
                    f"**{item.get('sequence_number', '')}. "
                    f"{topic_name}**"
                )

                st.caption(
                    f"{activity} · "
                    f"{item.get('estimated_minutes') or 0} min · "
                    f"Status: {status_label}"
                )

                reason = item.get("recommendation_reason")

                if reason:
                    st.write(reason)

                if current_status == "completed":
                    button_label = "↩ Reopen activity"
                    new_status = "pending"
                    button_key = (
                        f"reopen_{item.get('plan_item_id')}"
                    )
                else:
                    button_label = "✓ Mark as completed"
                    new_status = "completed"
                    button_key = (
                        f"complete_{item.get('plan_item_id')}"
                    )

                if st.button(
                    button_label,
                    key=button_key,
                    use_container_width=False,
                ):
                    _handle_activity_update(
                        user_id=user_id,
                        item=item,
                        new_status=new_status,
                    )

                if item_index < len(day_items) - 1:
                    st.divider()


def render_study_plan(learner):
    """Generate or retrieve the signed-in learner's Python study plan."""

    render_page_header(
        "PERSONALIZED LEARNING",
        "Your study plan",
        "A practical schedule shaped by your topic progress, course prerequisites, "
        "learning goal, and available study time. Recommendations use transparent "
        "rules based on assessment evidence.",
    )

    user_id = str(learner["user_id"])

    if "study_plan_notice" in st.session_state:
        st.success(st.session_state.pop("study_plan_notice"))

    profile_daily_minutes = learner.get("daily_study_minutes") or 45
    profile_daily_minutes = max(
        10,
        min(int(profile_daily_minutes), 600),
    )

    # Administrators may inspect their own saved plan while the course is
    # unpublished, but plan generation stays disabled until publication.
    can_generate_plan = True
    if learner.get("role") == "admin":
        try:
            can_generate_plan = is_course_published("python-basics")
        except (ValueError, RuntimeError, psycopg.Error):
            st.error(
                "We couldn't verify course publication status. "
                "Please refresh and try again."
            )
            return

    plan_days = 7
    daily_minutes = profile_daily_minutes
    submitted = False

    if can_generate_plan:
        with st.form("edupath_study_plan_form"):
            left, right = st.columns(2)

            plan_days = left.number_input(
                "Plan duration (days)",
                min_value=1,
                max_value=30,
                value=7,
                step=1,
                help=(
                    "The planner may extend this period when your daily "
                    "time is limited."
                ),
            )

            daily_minutes = right.number_input(
                "Daily study target (minutes)",
                min_value=10,
                max_value=600,
                value=profile_daily_minutes,
                step=5,
                help=(
                    "Defaults to the daily study target in your "
                    "learner profile."
                ),
            )

            submitted = st.form_submit_button(
                "Generate / refresh my study plan",
                type="primary",
                width="stretch",
            )
    else:
        st.info(
            "Python Programming is currently unpublished. You can still "
            "review your previously saved study plan, but creating a new "
            "plan is paused until the course is published."
        )

    plan = None

    if submitted:
        try:
            plan = generate_study_plan(
                user_id=user_id,
                course_slug="python-basics",
                days=int(plan_days),
                daily_minutes=int(daily_minutes),
            )

            st.success("Your personalized study plan has been saved.")

        except PermissionError as error:
            st.error(str(error))

        except ValueError as error:
            st.error(
                f"We couldn't generate this study plan: {error}"
            )

        except (RuntimeError, psycopg.Error):
            st.error(
                "We couldn't save your study plan right now. "
                "Please try again."
            )

    else:
        try:
            plan = fetch_active_study_plan(
                user_id=user_id,
                course_slug="python-basics",
            )

        except ValueError as error:
            st.error(str(error))

        except (RuntimeError, psycopg.Error):
            st.error(
                "We couldn't load your saved study plan right now. "
                "Please try again."
            )

    if plan is None:
        if can_generate_plan:
            st.info(
                "You don't have a study plan yet. Choose your schedule "
                "above and generate your first personalized plan."
            )
        else:
            st.info(
                "There is no saved study plan for this course yet. "
                "A new plan can be generated after the course is published."
            )
        return

    _display_plan(plan, user_id)
