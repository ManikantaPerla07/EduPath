"""Dedicated Learner Analytics View for EduPath.

Fulfills Phase D4 requirements:
- Learner-facing analytics restricted strictly to authenticated user_id.
- Real historical assessment attempts, scores, and completion status.
- Topic mastery breakdown (Mastered, Developing, Needs Revision).
- Formative misconception history with corrective advice.
- Timestamped activity records without fictitious or simulated charts.
"""

from typing import Any
import psycopg
from psycopg.rows import dict_row
import streamlit as st

from services.assessment_service import load_database_url
from services.progress_service import fetch_learner_topic_progress
from services.misconception_service import fetch_active_learner_misconceptions
from ui.theme import render_page_header


def _fetch_learner_assessment_history(user_id: str) -> list[dict[str, Any]]:
    """Retrieve historical assessment sessions for the authenticated learner."""
    try:
        with psycopg.connect(load_database_url(), connect_timeout=10, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        session_id,
                        assessment_type,
                        status,
                        started_at,
                        completed_at,
                        score_percent
                    FROM assessment_sessions
                    WHERE user_id = %s
                    ORDER BY started_at DESC
                    LIMIT 10;
                    """,
                    (user_id,),
                )
                return cursor.fetchall()
    except Exception:
        return []


def _fetch_learner_feedback_history(user_id: str) -> list[dict[str, Any]]:
    """Retrieve feedback submitted by learner on tutor responses."""
    try:
        with psycopg.connect(load_database_url(), connect_timeout=10, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        cmf.rating,
                        cmf.feedback_text,
                        cmf.created_at
                    FROM chat_message_feedback cmf
                    JOIN chat_messages cm ON cm.message_id = cmf.message_id
                    JOIN chat_sessions cs ON cs.session_id = cm.session_id
                    WHERE cs.user_id = %s
                    ORDER BY cmf.created_at DESC
                    LIMIT 5;
                    """,
                    (user_id,),
                )
                return cursor.fetchall()
    except Exception:
        return []


def render_learning_analytics(learner: dict[str, Any]) -> None:
    """Render the comprehensive Learning Analytics dashboard."""
    render_page_header(
        "LEARNER ANALYTICS",
        "Performance & Progress Analytics",
        "Transparent, data-backed insights on your Python assessments, topic masteries, and formative feedback.",
    )

    user_id = str(learner["user_id"])
    course_slug = "python-basics"

    # 1. Topic Progress & Mastery
    try:
        topic_progress = fetch_learner_topic_progress(user_id=user_id, course_slug=course_slug)
    except Exception:
        topic_progress = []

    total_attempts = sum(int(t.get("attempts_count") or 0) for t in topic_progress)
    total_correct = sum(int(t.get("correct_count") or 0) for t in topic_progress)
    overall_accuracy = (total_correct / total_attempts * 100.0) if total_attempts > 0 else 0.0

    mastered_count = sum(1 for t in topic_progress if t.get("mastery_status") == "candidate_for_mastery")
    developing_count = sum(1 for t in topic_progress if t.get("mastery_status") == "developing")
    needs_revision_count = sum(1 for t in topic_progress if t.get("mastery_status") == "needs_revision")
    not_assessed_count = len(topic_progress) - (mastered_count + developing_count + needs_revision_count)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Questions Answered", total_attempts)
    metric_cols[1].metric("Overall Accuracy", f"{overall_accuracy:.1f}%")
    metric_cols[2].metric("Topics Mastered", f"{mastered_count}/{len(topic_progress)}")
    metric_cols[3].metric("Needs Revision", needs_revision_count)

    st.divider()

    # 2. Topic Mastery Status Breakdown
    st.subheader("Topic Mastery Matrix")
    st.caption("Evidence-damped mastery score and current status across curriculum topics.")

    if topic_progress:
        for t in topic_progress:
            name = t.get("topic_name") or t.get("topic_slug", "Unknown")
            status = t.get("mastery_status", "not_assessed").replace("_", " ").title()
            mastery_score = float(t.get("mastery_score") or 0.0)
            attempts = int(t.get("attempts_count") or 0)
            accuracy = float(t.get("accuracy_percent") or 0.0)

            status_badge = {
                "Candidate For Mastery": "🟢 Mastered",
                "Developing": "🟡 Developing",
                "Needs Revision": "🔴 Needs Revision",
                "Not Assessed": "⚪ Not Assessed",
            }.get(status, status)

            with st.container(border=True):
                top_cols = st.columns([3, 1])
                top_cols[0].markdown(f"**{name}** — {status_badge}")
                top_cols[1].caption(f"{attempts} attempts | {accuracy:.1f}% acc")
                st.progress(
                    max(0.0, min(mastery_score / 100.0, 1.0)),
                    text=f"Mastery Evidence Score: {mastery_score:.1f}%",
                )
    else:
        st.info("No topic progress recorded yet. Complete your first diagnostic assessment to populate analytics.")

    st.divider()

    # 3. Assessment History
    st.subheader("Assessment History")
    st.caption("Authoritative diagnostic and practice quiz sessions.")

    history = _fetch_learner_assessment_history(user_id)
    if history:
        for sess in history:
            a_type = str(sess.get("assessment_type", "Assessment")).replace("_", " ").title()
            status = str(sess.get("status", "in_progress")).title()
            score = sess.get("score_percent")
            score_str = f"{float(score):.1f}%" if score is not None else "In Progress"
            started = str(sess.get("started_at", ""))[:19].replace("T", " ")

            with st.container(border=True):
                h_cols = st.columns([2, 1, 1, 1])
                h_cols[0].markdown(f"**{a_type}**")
                h_cols[1].caption(f"Started: {started}")
                h_cols[2].caption(f"Status: {status}")
                h_cols[3].metric("Score", score_str)
    else:
        st.info("No assessment sessions completed yet.")

    st.divider()

    # 4. Formative Misconception Diagnostics
    st.subheader("Formative Misconception Analysis")
    st.caption("Active misconception patterns detected during subjective exercises and tutor interactions.")

    misconceptions = fetch_active_learner_misconceptions(user_id)
    if misconceptions:
        for m in misconceptions:
            code = m.get("misconception_code", "Unknown")
            topic = m.get("topic_slug", "").title()
            desc = m.get("short_description", "")
            corr = m.get("corrective_explanation", "")
            method = m.get("detection_method", "rule_based")

            with st.container(border=True):
                st.markdown(f"**`{code}`** ({topic})")
                st.write(f"**Misconception:** {desc}")
                st.success(f"**Corrective Insight:** {corr}")
                st.caption(f"Detected via {method} · Formative diagnostic record")
    else:
        st.success("No active misconceptions detected! Keep up the great conceptual work.")

    st.divider()

    # 5. Tutor Feedback History
    st.subheader("Tutor Interaction Feedback")
    st.caption("Ratings and notes you submitted on AI Tutor explanations.")

    feedback_rows = _fetch_learner_feedback_history(user_id)
    if feedback_rows:
        for fb in feedback_rows:
            rating = fb.get("rating", "Neutral")
            comment = fb.get("feedback_text") or "No comment provided"
            created = str(fb.get("created_at", ""))[:19].replace("T", " ")
            with st.container(border=True):
                st.markdown(f"**Rating:** {rating.title()} · <small>{created}</small>", unsafe_allow_html=True)
                st.caption(comment)
    else:
        st.caption("You have not submitted any tutor feedback yet. Use the thumbs up/down icons in AI Tutor chat to give feedback.")
