from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg

from services.assessment_service import load_database_url


GOOGLE_ISSUERS = {
    "https://accounts.google.com",
    "accounts.google.com",
}


def extract_google_identity(
    claims: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Extract the minimum Google identity information needed by EduPath.

    The Google subject, not the email address, identifies the account.

    Only pass claims obtained from Streamlit's authenticated st.user
    session. This function does not independently verify OAuth tokens.
    """

    if not isinstance(claims, Mapping):
        raise ValueError("Google identity claims must be a mapping.")

    issuer = claims.get("iss")
    subject = claims.get("sub")

    if not isinstance(issuer, str) or issuer not in GOOGLE_ISSUERS:
        raise ValueError("Unrecognized Google identity issuer.")

    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("A valid Google subject is required.")

    subject = subject.strip()

    if len(subject) > 255 or not subject.isascii():
        raise ValueError("Invalid Google subject identifier.")

    email = claims.get("email")

    if email is not None:
        if not isinstance(email, str):
            raise ValueError("Invalid email address.")

        email = email.strip() or None

    display_name = claims.get("name")

    if display_name is not None:
        if not isinstance(display_name, str):
            raise ValueError("Invalid display name.")

        display_name = display_name.strip() or None

    email_verified = claims.get("email_verified", False)

    if not isinstance(email_verified, bool):
        raise ValueError("Invalid email verification status.")

    return {
        "issuer": issuer,
        "subject": subject,
        "email": email,
        "email_verified": email_verified,
        "display_name": display_name,
    }


def get_or_create_learner(
    claims: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Create or retrieve a learner using their Google OIDC identity.

    Existing accounts are identified by issuer and subject.

    Security rules:
    - Google subject is used as the stable account identifier.
    - Disabled accounts are never automatically reactivated.
    - Inactive accounts are rejected without updating their details.
    - New learners receive the student role by database default.
    - New learner profiles start with adult_confirmation=False.
    - User and profile creation happen in one transaction.
    """

    identity = extract_google_identity(claims)

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:

        with connection.cursor() as cursor:

            # Create a new account or update an active existing account.
            #
            # The WHERE clause prevents updates to inactive accounts.
            # PostgreSQL returns no row when an inactive account conflicts.
            cursor.execute(
                """
                INSERT INTO users (
                    oidc_issuer,
                    oidc_subject,
                    email,
                    email_verified,
                    display_name
                )
                VALUES (%s, %s, %s, %s, %s)

                ON CONFLICT (oidc_issuer, oidc_subject)
                DO UPDATE SET
                    email = COALESCE(
                        EXCLUDED.email,
                        users.email
                    ),
                    email_verified = EXCLUDED.email_verified,
                    display_name = COALESCE(
                        EXCLUDED.display_name,
                        users.display_name
                    ),
                    updated_at = NOW()

                WHERE users.is_active = TRUE

                RETURNING
                    user_id,
                    role,
                    is_active,
                    email,
                    email_verified,
                    display_name;
                """,
                (
                    identity["issuer"],
                    identity["subject"],
                    identity["email"],
                    identity["email_verified"],
                    identity["display_name"],
                ),
            )

            user_row = cursor.fetchone()

            # No returned row can indicate an inactive account.
            # Check it separately without modifying its details.
            if user_row is None:

                cursor.execute(
                    """
                    SELECT
                        user_id,
                        is_active
                    FROM users
                    WHERE oidc_issuer = %s
                      AND oidc_subject = %s
                    FOR UPDATE;
                    """,
                    (
                        identity["issuer"],
                        identity["subject"],
                    ),
                )

                existing_user = cursor.fetchone()

                if existing_user is None:
                    raise RuntimeError(
                        "Unable to create or retrieve learner account."
                    )

                if not existing_user[1]:
                    raise PermissionError(
                        "This EduPath account is inactive. "
                        "Please contact an administrator."
                    )

                raise RuntimeError(
                    "Unable to update learner account."
                )

            (
                user_id,
                role,
                is_active,
                email,
                email_verified,
                display_name,
            ) = user_row

            # Additional safety check.
            if not is_active:
                raise PermissionError(
                    "This EduPath account is inactive. "
                    "Please contact an administrator."
                )

            # Create the learner profile only if it does not exist.
            #
            # Existing learning preferences and adult confirmation
            # are never overwritten during subsequent sign-ins.
            cursor.execute(
                """
                INSERT INTO learner_profiles (
                    user_id,
                    adult_confirmation
                )
                VALUES (%s, FALSE)

                ON CONFLICT (user_id) DO NOTHING

                RETURNING user_id;
                """,
                (user_id,),
            )

            profile_created = cursor.fetchone() is not None

            # Retrieve the persisted learner profile.
            cursor.execute(
                """
                SELECT
                    adult_confirmation,
                    proficiency_level,
                    preferred_language,
                    explanation_style,
                    daily_study_minutes
                FROM learner_profiles
                WHERE user_id = %s;
                """,
                (user_id,),
            )

            profile_row = cursor.fetchone()

            if profile_row is None:
                raise RuntimeError(
                    "Learner profile could not be retrieved."
                )

            (
                adult_confirmation,
                proficiency_level,
                preferred_language,
                explanation_style,
                daily_study_minutes,
            ) = profile_row

    return {
        "user_id": str(user_id),
        "role": role,
        "is_active": is_active,
        "email": email,
        "email_verified": email_verified,
        "display_name": display_name,
        "adult_confirmation": adult_confirmation,
        "proficiency_level": proficiency_level,
        "preferred_language": preferred_language,
        "explanation_style": explanation_style,
        "daily_study_minutes": daily_study_minutes,
        "profile_created": profile_created,
    }


def confirm_adult_status(user_id: str) -> None:
    """
    Save explicit adult confirmation for an authenticated learner.

    The caller must obtain user_id from the server-side learner account
    returned by get_or_create_learner(). Never trust a user ID supplied
    directly by a browser form.
    """

    try:
        learner_id = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid learner user ID is required.")

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:

        with connection.cursor() as cursor:
            # Serialize this profile write with account deactivation.
            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id = %s
                  AND is_active = TRUE
                FOR SHARE;
                """,
                (learner_id,),
            )

            if cursor.fetchone() is None:
                raise PermissionError(
                    "An active learner account is required."
                )

            cursor.execute(
                """
                UPDATE learner_profiles
                SET adult_confirmation = TRUE,
                    updated_at = NOW()
                WHERE user_id = %s;
                """,
                (learner_id,),
            )

            if cursor.rowcount != 1:
                raise ValueError("Learner profile not found.")


VALID_PROFICIENCY_LEVELS = {"beginner", "intermediate", "advanced"}
VALID_EXPLANATION_STYLES = {"simple", "step_by_step", "example_first"}
MIN_DAILY_STUDY_MINUTES = 10
MAX_DAILY_STUDY_MINUTES = 600
MAX_GOAL_LENGTH = 500
MAX_LANGUAGE_LENGTH = 50


def get_learner_profile(user_id: str) -> dict[str, Any]:
    """Retrieve the full profile for an active, authenticated learner."""
    try:
        learner_id = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid learner user ID is required.")

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.user_id,
                    u.email,
                    u.display_name,
                    u.role,
                    u.is_active,
                    lp.adult_confirmation,
                    lp.proficiency_level,
                    lp.preferred_language,
                    lp.explanation_style,
                    lp.daily_study_minutes,
                    lp.learning_goal
                FROM users AS u
                JOIN learner_profiles AS lp
                    ON lp.user_id = u.user_id
                WHERE u.user_id = %s
                  AND u.is_active = TRUE;
                """,
                (learner_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Learner account or profile not found.")

            return {
                "user_id": str(row[0]),
                "email": row[1],
                "display_name": row[2],
                "role": row[3],
                "is_active": row[4],
                "adult_confirmation": row[5],
                "proficiency_level": row[6],
                "preferred_language": row[7],
                "explanation_style": row[8],
                "daily_study_minutes": row[9],
                "learning_goal": row[10],
            }


def update_learner_profile(
    user_id: str,
    *,
    proficiency_level: str | None = None,
    explanation_style: str | None = None,
    daily_study_minutes: int | None = None,
    preferred_language: str | None = None,
    learning_goal: str | None = None,
) -> dict[str, Any]:
    """
    Update learner profile preferences with server-side validation.

    Only provided non-None values are updated. All fields are validated
    against schema constraints.
    """
    try:
        learner_id = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid learner user ID is required.")

    set_clauses = []
    params = []

    if proficiency_level is not None:
        if not isinstance(proficiency_level, str) or proficiency_level.lower().strip() not in VALID_PROFICIENCY_LEVELS:
            raise ValueError(
                f"Proficiency level must be one of: {', '.join(sorted(VALID_PROFICIENCY_LEVELS))}."
            )
        set_clauses.append("proficiency_level = %s")
        params.append(proficiency_level.lower().strip())

    if explanation_style is not None:
        if not isinstance(explanation_style, str) or explanation_style.lower().strip() not in VALID_EXPLANATION_STYLES:
            raise ValueError(
                f"Explanation style must be one of: {', '.join(sorted(VALID_EXPLANATION_STYLES))}."
            )
        set_clauses.append("explanation_style = %s")
        params.append(explanation_style.lower().strip())

    if daily_study_minutes is not None:
        if (
            isinstance(daily_study_minutes, bool)
            or not isinstance(daily_study_minutes, int)
            or not MIN_DAILY_STUDY_MINUTES <= daily_study_minutes <= MAX_DAILY_STUDY_MINUTES
        ):
            raise ValueError(
                f"Daily study minutes must be an integer between {MIN_DAILY_STUDY_MINUTES} and {MAX_DAILY_STUDY_MINUTES}."
            )
        set_clauses.append("daily_study_minutes = %s")
        params.append(daily_study_minutes)

    if preferred_language is not None:
        if not isinstance(preferred_language, str) or not preferred_language.strip():
            raise ValueError("Preferred language cannot be empty.")
        lang = preferred_language.strip()
        if len(lang) > MAX_LANGUAGE_LENGTH:
            raise ValueError(f"Preferred language cannot exceed {MAX_LANGUAGE_LENGTH} characters.")
        set_clauses.append("preferred_language = %s")
        params.append(lang)

    if learning_goal is not None:
        if not isinstance(learning_goal, str):
            raise ValueError("Learning goal must be a string.")
        goal = learning_goal.strip()
        if len(goal) > MAX_GOAL_LENGTH:
            raise ValueError(f"Learning goal cannot exceed {MAX_GOAL_LENGTH} characters.")
        set_clauses.append("learning_goal = %s")
        params.append(goal if goal else None)

    if not set_clauses:
        # Nothing to update, just return current profile
        return get_learner_profile(user_id)

    set_clauses.append("updated_at = NOW()")

    with psycopg.connect(
        load_database_url(),
        connect_timeout=20,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id = %s
                  AND is_active = TRUE
                FOR SHARE;
                """,
                (learner_id,),
            )
            if cursor.fetchone() is None:
                raise PermissionError("An active learner account is required.")

            query = f"""
                UPDATE learner_profiles
                SET {', '.join(set_clauses)}
                WHERE user_id = %s
                RETURNING
                    user_id,
                    proficiency_level,
                    preferred_language,
                    explanation_style,
                    daily_study_minutes,
                    learning_goal,
                    adult_confirmation;
            """
            params.append(learner_id)
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Learner profile not found.")

            return {
                "user_id": str(row[0]),
                "proficiency_level": row[1],
                "preferred_language": row[2],
                "explanation_style": row[3],
                "daily_study_minutes": row[4],
                "learning_goal": row[5],
                "adult_confirmation": row[6],
            }
