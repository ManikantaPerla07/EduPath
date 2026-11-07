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
